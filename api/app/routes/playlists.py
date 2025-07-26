from typing import Literal, Optional
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials

from ..db import db
from ..models import Clip, Playlist, Video
from ..routes.auth import auth_scheme_optional, get_current_user
from ..utils import convert_objectid

router = APIRouter()


async def get_all_playlists() -> list:
    playlists = await db.playlists.find().to_list(length=None)
    return playlists


# Get all playlists where the given id is the direct owner
async def get_playlist_by_owner(id: str) -> list:
    return await db.playlists.find({"owner_id": ObjectId(id)}).to_list(length=None)


async def get_playlist_by_member(user_id: str) -> list:
    user_oid = ObjectId(user_id)

    # Find all teams where this user is a member
    teams = await db.teams.find({"member_ids": user_oid}).to_list(length=None)
    team_ids = [team["_id"] for team in teams]

    # Find all playlists that belong to the team(s) the user is a member of
    return await db.playlists.find({"team_id": {"$in": team_ids}}).to_list(length=None)


async def get_playlists_for_user(user_id: str) -> list:
    owned = await get_playlist_by_owner(user_id)
    member = await get_playlist_by_member(user_id)
    filtered_member = [p for p in member if p["_id"] not in {pl["_id"] for pl in owned}]
    return {"owned": owned, "member": filtered_member}


async def get_playlist_by_name(name: str):
    return await db.playlists.find_one({"name": name})


async def get_video_by_id(playlist_name: str, video_id: str):
    return await db.playlists.find_one({"name": playlist_name, "videos.video_id": video_id})


async def insert_playlist(playlist: Playlist):
    await db.playlists.insert_one(playlist.dict())


async def insert_video(playlist_name: str, video: Video):
    await db.playlists.update_one({"name": playlist_name}, {"$push": {"videos": video.dict()}})


async def insert_clip(playlist_name: str, video_id: str, clip: Clip):
    await db.playlists.update_one(
        {"name": playlist_name, "videos.video_id": video_id},
        {"$push": {"videos.$.clips": clip.dict()}},
    )


# playlist
@router.get("/playlists")
async def get_playlists(
    user_id: Optional[str] = Query(None),
    filter: Literal["owned", "member", "all"] = "all",
    token: HTTPAuthorizationCredentials = Depends(auth_scheme_optional),
):
    if user_id:
        # TODO: get rid of this query functionality in the api, and use the filter in the frontend instead
        # TODO: owned and member filters are not tested, and are inconsistent with all's response
        if filter == "owned":
            playlists = await get_playlist_by_owner(user_id)
        elif filter == "member":
            playlists = await get_playlist_by_member(user_id)
        else:  # filter == "all"
            playlists = await get_playlists_for_user(user_id)
    else:
        playlists = await get_all_playlists()
    return convert_objectid(playlists)


# TODO: use insert_playlist() function to insert playlists
@router.post("/playlists")
async def create_playlist(playlist: Playlist, user=Depends(get_current_user)):
    existing_playlist = await get_playlist_by_name(playlist.name)
    if existing_playlist:
        raise HTTPException(status_code=400, detail="Playlist already exists.")

    playlist_dict = playlist.dict(by_alias=True)

    # Default owner_id to authenticated user
    if not playlist.owner_id:
        playlist_dict["owner_id"] = user["_id"]

    await db.playlists.insert_one(playlist_dict)
    return {"msg": "Playlist created successfully!"}


@router.get("/playlists/{playlist_name}")
async def get_playlist(
    playlist_name: str,
    _: HTTPAuthorizationCredentials = Depends(auth_scheme_optional),
):
    playlist = await get_playlist_by_name(playlist_name)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found.")
    return convert_objectid(playlist)


@router.post("/playlists/{playlist_name}/videos")
async def create_video(playlist_name: str, video: Video, user=Depends(get_current_user)):

    playlist = await get_playlist_by_name(playlist_name)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found.")

    if not playlist["owner_id"] == user["_id"]:
        raise HTTPException(status_code=403, detail="Access denied to this playlist.")

    existing_video = await get_video_by_id(playlist_name, video.video_id)
    if existing_video:
        raise HTTPException(status_code=400, detail="Video already exists.")

    await insert_video(playlist_name, video)
    return {"msg": "Video added to playlist!"}  # TODO: return video object or something?


@router.post("/playlists/{playlist_name}/videos/{video_id}/clips")
async def create_clip(playlist_name: str, video_id: str, clip: Clip, user=Depends(get_current_user)):
    playlist = await get_playlist_by_name(playlist_name)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found.")
    if not playlist["owner_id"] == user["_id"]:
        raise HTTPException(status_code=403, detail="Access denied to this playlist.")

    video = await get_video_by_id(playlist_name, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")

    if not clip.clip_id:
        clip.clip_id = str(uuid4())

    await insert_clip(playlist_name, video_id, clip)
    return {"msg": "Clip added to video!"}


@router.put("/playlists/{playlist_name}/videos")
async def update_video(playlist_name: str, updated_video: Video, user=Depends(get_current_user)):
    playlist = await get_playlist_by_name(playlist_name)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found.")

    # Extend access: allow playlist owner OR users from the team with access
    is_owner = playlist["owner_id"] == user["_id"]
    user_team_ids = set(user.get("team_ids", []))
    playlist_team_id = playlist.get("team_id")
    is_team_member = playlist_team_id in user_team_ids

    if not (is_owner or is_team_member):
        raise HTTPException(status_code=403, detail="Access denied to this playlist.")

    videos = playlist.get("videos", [])
    for i, video in enumerate(videos):
        if video["video_id"] == updated_video.video_id:
            # Preserve clip_id for existing clips
            existing_clips = {clip["clip_id"]: clip for clip in video.get("clips", [])}
            incoming_clips = []

            for clip in updated_video.clips:
                clip_dict = clip.dict()
                clip_id = clip_dict.get("clip_id")

                if clip_id in existing_clips:
                    # Merge old and new to preserve extra fields (if any)
                    merged_clip = {**existing_clips[clip_id], **clip_dict}
                else:
                    # New clip → generate new ID if not already present
                    if not clip_id:
                        from uuid import uuid4

                        clip_dict["clip_id"] = str(uuid4())
                    merged_clip = clip_dict

                incoming_clips.append(merged_clip)

            # Build the updated video object
            updated_data = updated_video.dict()
            updated_data["video_id"] = video.get("video_id")
            updated_data["youtube_url"] = video.get("youtube_url")
            updated_data["date"] = video.get("date")
            updated_data["title"] = video.get("title")
            updated_data["duration_seconds"] = video.get("duration_seconds")
            updated_data["added_date"] = video.get("added_date")
            updated_data["clips"] = incoming_clips
            videos[i] = updated_data

            await db.playlists.update_one({"name": playlist_name}, {"$set": {"videos": videos}})
            return {"msg": "Video updated successfully!"}

    raise HTTPException(status_code=404, detail="Video not found in playlist.")


@router.put("/playlists/{playlist_name}/assign-team")
async def assign_playlist_to_team(playlist_name: str, team_id: str, user=Depends(get_current_user)):
    user_id = user["_id"]

    # 1. Check if playlist exists and is owned by the user
    playlist = await get_playlist_by_name(playlist_name)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found or not owned by user.")
    if not playlist["owner_id"] == user_id:
        raise HTTPException(status_code=403, detail="Access denied to this playlist.")

    # 2. Check if the team exists and user is a member
    team = await db.teams.find_one({"_id": ObjectId(team_id), "member_ids": user_id})
    if not team:
        raise HTTPException(status_code=403, detail="User not a member of this team.")

    # 3. Assign playlist to team
    await db.playlists.update_one({"name": playlist_name}, {"$set": {"team_id": ObjectId(team_id)}})

    return {"msg": "Playlist assigned to team successfully."}


@router.put("/playlists/{playlist_name}/videos/{video_id}/clips")
async def update_clip(
    playlist_name: str,
    video_id: str,
    clip: Clip = Body(...),
    user=Depends(get_current_user),
):
    playlist = await get_playlist_by_name(playlist_name)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found.")
    if not playlist["owner_id"] == user["_id"]:
        raise HTTPException(status_code=403, detail="Access denied to this playlist.")

    video = await get_video_by_id(playlist_name, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")

    # Find and update the clip by title and start time (or use a unique id if you have one)
    updated = False
    for v in playlist.get("videos", []):
        if v["video_id"] == video_id:
            for i, c in enumerate(v.get("clips", [])):
                # You can use a better unique identifier if available
                if c.get("clip_id") == clip.clip_id:
                    v["clips"][i] = clip.dict()
                    updated = True
                    break
            if not updated:
                raise HTTPException(status_code=404, detail="Clip not found.")
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Clip not found.")

    await db.playlists.update_one({"name": playlist_name}, {"$set": {"videos": playlist["videos"]}})
    return {"msg": "Clip updated successfully!"}

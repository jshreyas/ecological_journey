# # ---------------- app/routes.py ----------------
# from fastapi import APIRouter, Depends
# from .models import Video
# from .db import db
# from .auth import verify_token
# from bson import ObjectId

# router = APIRouter()

# @router.get("/videos")
# async def get_videos():
#     videos = await db.videos.find().to_list(100)
#     # Convert ObjectId to string for each video
#     for video in videos:
#         video["_id"] = str(video["_id"])
#     return videos

# @router.post("/videos")
# async def add_video(video: Video, user=Depends(verify_token)): # TODO:
# # async def add_video(video: Video):
#     video_dict = video.dict()
#     result = await db.videos.insert_one(video_dict)
#     return {"inserted_id": str(result.inserted_id)}
##
from fastapi import APIRouter, HTTPException, Depends
from .models import Playlist, Video, Clip
from typing import List
from .db import db
from bson import ObjectId
from .auth import verify_token

router = APIRouter()

# Utility functions

def convert_objectid(data):
    if isinstance(data, list):
        return [convert_objectid(item) for item in data]
    elif isinstance(data, dict):
        return {
            key: convert_objectid(value)
            for key, value in data.items()
        }
    elif isinstance(data, ObjectId):
        return str(data)
    else:
        return data


async def get_playlist_by_name(name: str):
    return await db.playlists.find_one({"name": name})

async def get_all_playlists():
    playlists_cursor = db.playlists.find()
    return await playlists_cursor.to_list(length=None)

async def get_video_by_id(playlist_name: str, video_id: str):
    return await db.playlists.find_one({"name": playlist_name, "videos.video_id": video_id})


async def insert_playlist(playlist: Playlist):
    await db.playlists.insert_one(playlist.dict())


async def insert_video(playlist_name: str, video: Video):
    await db.playlists.update_one(
        {"name": playlist_name},
        {"$push": {"videos": video.dict()}}
    )


async def insert_clip(playlist_name: str, video_id: str, clip: Clip):
    await db.playlists.update_one(
        {"name": playlist_name, "videos.video_id": video_id},
        {"$push": {"videos.$.clips": clip.dict()}}
    )

# Routes
@router.get("/playlists", response_model=List[Playlist])
async def get_playlist():
    playlists = await get_all_playlists()
    return convert_objectid(playlists)

@router.post("/playlists")
async def create_playlist(playlist: Playlist, user=Depends(verify_token)):
    existing_playlist = await get_playlist_by_name(playlist.name)
    if existing_playlist:
        raise HTTPException(status_code=400, detail="Playlist already exists.")
    await insert_playlist(playlist)
    return {"msg": "Playlist created successfully!"}

@router.get("/playlists/{playlist_name}")
async def get_playlist(playlist_name: str):
    playlist = await get_playlist_by_name(playlist_name)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found.")
    return convert_objectid(playlist)

@router.post("/playlists/{playlist_name}/videos")
async def create_video(playlist_name: str, video: Video, user=Depends(verify_token)):
    playlist = await get_playlist_by_name(playlist_name)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found.")

    existing_video = await get_video_by_id(playlist_name, video.video_id)
    if existing_video:
        raise HTTPException(status_code=400, detail="Video already exists.")
    
    await insert_video(playlist_name, video)
    return {"msg": "Video added to playlist!"}

@router.post("/playlists/{playlist_name}/videos/{video_id}/clips")
async def create_clip(playlist_name: str, video_id: str, clip: Clip, user=Depends(verify_token)):
    video = await get_video_by_id(playlist_name, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")
    
    await insert_clip(playlist_name, video_id, clip)
    return {"msg": "Clip added to video!"}

@router.put("/playlists/{playlist_name}/videos")
async def update_video(playlist_name: str, updated_video: Video, user=Depends(verify_token)):
    # Fetch the playlist and ensure video exists
    playlist = await get_playlist_by_name(playlist_name)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found.")
    
    videos = playlist.get("videos", [])
    for i, video in enumerate(videos):
        if video["video_id"] == updated_video.video_id:
            # Preserve immutable fields
            updated_data = updated_video.dict()
            updated_data["video_id"] = video.get("video_id")
            updated_data["youtube_url"] = video.get("youtube_url")
            updated_data["date"] = video.get("date")
            updated_data["title"] = video.get("title")
            updated_data["duration_seconds"] = video.get("duration_seconds")
            updated_data["added_date"] = video.get("added_date")
            # updated_data["_id"] = video.get("_id", None)  # optional if _id exists

            # Update the video in-place
            videos[i] = updated_data

            # Push the entire updated videos list back to DB
            await db.playlists.update_one(
                {"name": playlist_name},
                {"$set": {"videos": videos}}
            )
            return {"msg": "Video updated successfully!"}

    raise HTTPException(status_code=404, detail="Video not found in playlist.")

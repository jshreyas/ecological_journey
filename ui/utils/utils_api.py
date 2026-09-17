from typing import Any, Dict, List, Optional

from ui.data.crud import add_video_to_playlist, create_cliplist
from ui.data.crud import create_playlist as create_playlist_record
from ui.data.crud import create_team as create_team_record
from ui.data.crud import (
    edit_video_in_playlist,
    load_cliplist,
    load_notion_latest,
    load_playlist,
    load_playlists,
    load_teams,
)
from ui.data.models import User
from ui.utils.cache import CACHE_TTL, cache_result
from ui.utils.utils import parse_query_expression


def get_notion_tree():
    return load_notion_latest()["tree"]


def create_team(*, name: str, user: User) -> dict[str, Any]:
    return create_team_record(name=name, user=user)


def fetch_teams_for_user(user_id: str) -> List[Dict[str, Any]]:
    teams = load_teams()
    response = {
        "owned": [team for team in teams if team.get("owner_id") == user_id],
        "member": [team for team in teams if user_id in team.get("member_ids", [])],
    }
    return response


def create_playlist(
    *,
    video_data: list[dict[str, Any]],
    name: str,
    playlist_id: str,
    user: User,
) -> dict[str, Any]:
    return create_playlist_record(
        name=name,
        playlist_id=playlist_id,
        videos=video_data,
        user=user,
    )


def create_video(
    *,
    video_data: list[dict[str, Any]],
    playlist_id: str,
    user: User,
) -> dict[str, Any]:
    return add_video_to_playlist(
        playlist_id=playlist_id,
        new_videos=video_data,
        user=user,
    )


def load_playlists_for_user(user_id: str, filter: str = "all") -> Dict[str, List[Dict[str, Any]]]:
    playlists = load_playlists()
    teams = fetch_teams_for_user(user_id)
    # Combine all teams if teams is a dict (API returns {'owned': [], 'member': []})
    if isinstance(teams, dict):
        all_teams = (teams.get("owned", []) or []) + (teams.get("member", []) or [])
    else:
        all_teams = teams or []
    user_team_ids = {team.get("_id") for team in all_teams if user_id in team.get("member_ids", [])}

    owned = [pl for pl in playlists if pl.get("owner_id") == user_id]
    member = [pl for pl in playlists if pl.get("owner_id") != user_id and pl.get("team_id") in user_team_ids]
    # Remove duplicates by _id
    owned_ids = {pl["_id"] for pl in owned}
    filtered_member = [pl for pl in member if pl["_id"] not in owned_ids]

    if filter == "owned":
        return {"owned": owned, "member": []}
    elif filter == "member":
        return {"owned": [], "member": filtered_member}
    else:  # "all"
        return {"owned": owned, "member": filtered_member}


def format_duration(seconds: int) -> str:
    """Convert seconds into a human-readable format (HH:MM:SS or MM:SS)."""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"  # HH:MM:SS
    return f"{int(minutes):02}:{int(seconds):02}"  # MM:SS


def load_videos(
    playlist_id: Optional[str] = None,
    response_dict: bool = False,
):
    playlists = load_playlists()
    videos = []

    for pl in playlists:
        if playlist_id and pl["_id"] != playlist_id:
            continue

        full = load_playlist(pl["_id"])
        if not full:
            continue

        for video in full.get("videos", []):
            enriched = {
                **video,
                "playlist_id": full["_id"],
                "playlist_name": full["name"],
                "playlist_color": full["color"],
                "duration_human": format_duration(video.get("duration_seconds", 0)),
            }
            videos.append(enriched)
    videos.sort(key=lambda x: x.get("date", ""), reverse=True)
    return {v["video_id"]: v for v in videos} if response_dict else videos


@cache_result("clips:index", ttl_seconds=CACHE_TTL)
def load_clips() -> List[Dict[str, Any]]:
    clips = []

    playlists_index = load_playlists()  # lightweight index

    for playlist_meta in playlists_index:
        playlist = load_playlist(playlist_meta["_id"])
        if not playlist:
            continue

        for video in playlist.get("videos", []):
            for clip in video.get("clips", []):
                partners = (clip.get("partners") or []) + (video.get("partners") or [])
                labels = (clip.get("labels") or []) + (video.get("labels") or [])

                clips.append(
                    {
                        "video_id": video["video_id"],
                        "playlist_id": playlist["_id"],
                        "playlist_name": playlist["name"],
                        "start": clip.get("start", 0),
                        "end": clip.get("end", 0),
                        "title": clip.get("title", ""),
                        "date": video.get("date", ""),
                        "duration_human": format_duration(clip.get("end", 0) - clip.get("start", 0)),
                        "description": clip.get("description", ""),
                        "partners": partners,
                        "labels": labels,
                        "type": clip.get("type", "clip"),
                        "clip_id": clip.get("clip_id", ""),
                    }
                )

    clips.sort(key=lambda x: x.get("date", ""), reverse=True)
    return clips


def save_video_metadata(
    *,
    video_metadata: dict[str, Any],
    user: User,
) -> dict[str, Any]:
    return edit_video_in_playlist(
        playlist_id=video_metadata["playlist_id"],
        updated_video=video_metadata,
        user=user,
    )


def save_cliplist(
    *,
    name: str,
    filters_state: dict[str, Any],
    user: User,
) -> dict[str, Any]:
    return create_cliplist(
        name=name,
        filters=filters_state,
        user=user,
    )


def get_filtered_clips(cliplist_id: str) -> List[Dict[str, Any]]:
    all_videos = load_clips()
    cliplist = load_cliplist(cliplist_id)
    filters_to_use = cliplist.get("filters", {})

    parsed_fn = (
        parse_query_expression(filters_to_use.get("labels")) if filters_to_use.get("labels") else lambda labels: True
    )
    pparsed_fn = (
        parse_query_expression(filters_to_use.get("partners"))
        if filters_to_use.get("partners")
        else lambda partners: True
    )
    date_range = filters_to_use.get("date_range", [])
    has_date_filter = len(date_range) == 2

    return [
        v
        for v in all_videos
        if v["playlist_name"] in filters_to_use.get("playlists", [])
        and (not has_date_filter or (date_range[0] <= v["date"][:10] <= date_range[1]))
        and parsed_fn(v.get("labels", []))
        and pparsed_fn(v.get("partners", []))
    ]

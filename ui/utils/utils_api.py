import os
from typing import Any, Dict, List, Optional, Union

import requests
from data.crud import add_video_to_playlist, create_cliplist
from data.crud import create_playlist as cp
from data.crud import create_team as ct
from data.crud import load_cliplist, load_notion_latest, load_playlists, load_teams
from dotenv import load_dotenv
from utils.cache import cache_del, cache_get, cache_set
from utils.utils import format_time, parse_query_expression

load_dotenv()

BASE_URL = os.getenv("BACKEND_URL")
_playlists_cache: Optional[List[Dict[str, Any]]] = None  # file-level in-memory cache
_cliplist_cache: Dict[str, Any] = {}


# TODO: currecntly clears the 2 heavy hitters, how about the rest and parameterization?
def clear_cache() -> None:
    """Clear both in-memory and Redis caches."""
    # Clear in-process memory
    global _cliplist_cache, _playlists_cache
    _cliplist_cache = {}
    _playlists_cache = None

    # Clear Redis
    cache_del("cliplists")
    cache_del("playlists")


def get_headers(token: Optional[str] = None) -> Dict[str, str]:
    """Get headers for API requests."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def api_get(endpoint: str, token: Optional[str] = None) -> Any:
    """Make a GET request to the API."""
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def api_post(endpoint: str, data: dict, token: Optional[str] = None) -> Any:
    """Make a POST request to the API."""
    url = f"{BASE_URL}{endpoint}"
    response = requests.post(url, json=data, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def api_put(endpoint: str, data: dict, token: Optional[str] = None) -> Any:
    """Make a PUT request to the API."""
    url = f"{BASE_URL}{endpoint}"
    response = requests.put(url, json=data, headers=get_headers(token))
    response.raise_for_status()
    return response.json()


def trigger_fetch_notion() -> None:
    """Trigger a Notion tree refresh."""
    response = api_post("/fetch_notion", data={})  # Trigger backend to refresh Notion tree
    print(f"Triggered Notion tree refresh: {response}")
    return response


def get_notion_tree():
    return load_notion_latest()["tree"]


def create_team(name: str, token: str, user_id: str) -> Any:
    """Create a new team and refresh cache."""
    return ct(name=name, token=token)


def fetch_teams_for_user(user_id: str) -> List[Dict[str, Any]]:
    teams = load_teams()
    response = {
        "owned": [team for team in teams if team.get("owner_id") == user_id],
        "member": [team for team in teams if user_id in team.get("member_ids", [])],
    }
    return response


def create_playlist(video_data: List[Dict[str, Any]], token: str, name: str, playlist_id: str) -> Any:
    """Create a new playlist with videos."""
    return cp(name=name, playlist_id=playlist_id, videos=video_data, token=token)


def create_video(video_data: List[Dict[str, Any]], token: str, playlist_id: str) -> None:
    """Create videos in a playlist."""
    return add_video_to_playlist(playlist_id=playlist_id, new_videos=video_data, token=token)


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


def _refresh_playlists_cache() -> None:
    """Force refresh playlists from backend and update both Redis and in-memory cache."""
    global _playlists_cache
    playlists = api_get("/playlists")
    cache_set("playlists", playlists)
    _playlists_cache = playlists


def format_duration(seconds: int) -> str:
    """Convert seconds into a human-readable format (HH:MM:SS or MM:SS)."""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"  # HH:MM:SS
    return f"{int(minutes):02}:{int(seconds):02}"  # MM:SS


def load_videos(
    playlist_id: Optional[str] = None, response_dict: bool = False
) -> Union[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Load videos from playlists, optionally returning as a dictionary."""
    playlists = load_playlists()
    videos = []
    for playlist in playlists:
        if playlist_id is None or playlist.get("_id") == playlist_id:
            for video in playlist.get("videos", []):
                video["playlist_id"] = playlist.get("_id")
                video["playlist_name"] = playlist.get("name")
                # Add human-readable duration to each video
                video["duration_human"] = format_duration(video.get("duration_seconds", 0))
                videos.append(video)
    videos.sort(key=lambda x: x.get("date", ""), reverse=True)
    if response_dict:
        return {video["video_id"]: video for video in videos if "video_id" in video}
    return videos


def load_video(video_id: str) -> Optional[Dict[str, Any]]:
    """Return a single video dict by video_id, or None if not found."""
    videos = load_videos(response_dict=True)
    return videos.get(video_id)


def get_playlist_id_for_video(video_id: str) -> Optional[str]:
    playlists = load_playlists()
    for playlist in playlists:
        for video in playlist.get("videos", []):
            if video.get("video_id") == video_id:
                return playlist.get("name")  # TODO: Fix usage of playlist name vs id
    return None


def load_clips() -> List[Dict[str, Any]]:
    clips = []
    playlists = load_playlists()
    for playlist in playlists:
        for video in playlist.get("videos", []):
            if video.get("clips", []):
                for clip in video["clips"]:
                    partners = (clip.get("partners") or []) + (video.get("partners") or [])
                    labels = (clip.get("labels") or []) + (video.get("labels") or [])
                    clip_data = {
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
                    clips.append(clip_data)
    clips.sort(key=lambda x: x.get("date", ""), reverse=True)
    return clips


def convert_clips_to_raw_text(video_id: str, video_duration: Optional[int] = None) -> str:
    videos = load_videos()
    video_metadata = next((v for v in videos if v["video_id"] == video_id), {})
    clips = video_metadata.get("clips", [])
    duration = video_duration or video_metadata.get("duration_seconds")

    lines = []

    has_metadata = any(video_metadata.get(k) for k in ["partners", "labels", "type", "notes"])
    has_clips = bool(clips)

    if has_metadata:
        if video_metadata.get("partners"):
            lines.append(" ".join(f"@{p}" for p in video_metadata["partners"]))
        if video_metadata.get("labels"):
            lines.append(" ".join(f"#{label}" for label in video_metadata["labels"]))
        if video_metadata.get("type"):
            lines.append(f"type: {video_metadata['type']}")
        if video_metadata.get("notes"):
            lines.append(f"notes: {video_metadata['notes']}")
        lines.append("")
    else:
        lines += [
            "@partner1 @partner2 #position1 #position2",
            "type: positional/sparring/rolling/instructional",
            "notes: optional general notes about this video",
            "",
        ]

    if not has_clips and duration:
        lines.append("00:00 - 00:30 | Clip Title Here | Optional description here @partner1 @partner2 #label1 #label2")
        clips = [{"start": 0, "end": duration, "type": "autogen"}]

    for clip in clips:
        start = clip.get("start", 0)
        end = clip.get("end", 0)
        if duration and end > duration:
            end = duration

        if clip.get("type") != "clip":
            lines.append(f"{format_time(start)} - {format_time(end)} | Full video | @autogen")
            continue

        title = clip.get("title", "")
        description = clip.get("description", "")
        partners = " ".join(f"@{p}" for p in clip.get("partners", []))
        labels = " ".join(f"#{label}" for label in clip.get("labels", []))
        full_desc = " ".join(part for part in [description, partners, labels] if part)

        lines.append(f"{format_time(start)} - {format_time(end)} | {title} | {full_desc}")
    return "\n".join(lines)


def parse_clip_line(line: str) -> Optional[Dict[str, Any]]:
    try:
        if "Clip Title Here" in line or "@autogen" in line:
            return None

        import re

        match = re.match(
            r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s*\|\s*([^|]+)\s*(?:\|\s*(.*))?",
            line,
        )
        if not match:
            return None
        start_str, end_str, title, full_desc = match.groups()

        def to_seconds(t: str) -> int:
            minutes, seconds = map(int, t.strip().split(":"))
            return minutes * 60 + seconds

        full_desc = full_desc or ""
        partners = re.findall(r"@(\w+)", full_desc)
        labels = re.findall(r"#(\w+)", full_desc)
        description = re.sub(r"[@#]\w+", "", full_desc).strip()

        return {
            "start": to_seconds(start_str),
            "end": to_seconds(end_str),
            "title": title.strip(),
            "description": description,
            "type": "clip",
            "partners": partners,
            "labels": labels,
        }
    except Exception:
        return None


def get_all_partners() -> List[str]:
    cache_key = "all_partners"
    cached = cache_get(cache_key)
    if cached:
        return cached
    partners_set = set()
    videos = load_videos()
    for video in videos:
        video_partners = video.get("partners", [])
        partners_set.update(video_partners)
        clips = video.get("clips", [])
        for clip in clips:
            if clip.get("type") == "clip":
                partners_set.update(clip.get("partners", []))
    result = sorted(partners_set)
    cache_set(cache_key, result)
    return result


def find_clips_by_partner(partner: str) -> List[Dict[str, Any]]:
    result = []
    videos = load_videos()
    for video in videos:
        video_id = video["video_id"]
        video_partners = video.get("partners", [])
        clips = video.get("clips", [])
        for clip in clips:
            clip_partners = clip.get("partners", [])
            if partner in clip_partners or partner in video_partners:
                merged_labels = list(set(video.get("labels", []) + clip.get("labels", [])))
                combined = {
                    "video_id": video_id,
                    **video,
                    **clip,
                    "labels": merged_labels,
                }
                result.append(combined)
    return result


def convert_video_metadata_to_raw_text(video: dict) -> str:
    partners_line = " ".join(f"@{p}" for p in video.get("partners", []))
    labels_line = " ".join(f"#{label}" for label in video.get("labels", []))
    notes = video.get("notes", "")
    return "\n".join(filter(None, [partners_line, labels_line, notes]))


def save_video_metadata(video_metadata: dict, token: str) -> bool:
    playlist_name = get_playlist_id_for_video(video_metadata.get("video_id"))
    if not playlist_name:
        print(f"Could not find playlist for video_id: {video_metadata.get('video_id')}")
        return False
    try:
        api_put(f"/playlists/{playlist_name}/videos", data=video_metadata, token=token)
        _refresh_playlists_cache()
        return True
    except Exception as e:
        print(f"Failed to save video metadata: {e}")
        return False


def save_cliplist(name: str, filters_state: Dict[str, Any], token: str) -> Optional[Dict[str, Any]]:
    return create_cliplist(name=name, filters=filters_state, token=token)


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

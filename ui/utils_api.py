import os
import re
import requests
import json
import redis
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from utils import format_time
load_dotenv()

BASE_URL = os.getenv("BACKEND_URL")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Setup Redis client
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def cache_get(key: str):
    print(f"Fetching from cache for key: {key}")
    value = redis_client.get(key)
    if value:
        try:
            return json.loads(value)
        except Exception:
            return value
    return None

def cache_set(key: str, value, ex: int = 300):
    print(f"Caching key: {key} with value: {value}")
    try:
        redis_client.set(key, json.dumps(value), ex=ex)
    except Exception as e:
        print(f"Redis set error: {e}")

def get_headers(token: Optional[str] = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def api_get(endpoint: str, token: Optional[str] = None):
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, headers=get_headers(token))
    response.raise_for_status()
    return response.json()

def api_post(endpoint: str, data: dict, token: Optional[str] = None):
    url = f"{BASE_URL}{endpoint}"
    response = requests.post(url, json=data, headers=get_headers(token))
    response.raise_for_status()
    return response.json()

def api_put(endpoint: str, data: dict, token: Optional[str] = None):
    url = f"{BASE_URL}{endpoint}"
    response = requests.put(url, json=data, headers=get_headers(token))
    response.raise_for_status()
    return response.json()

def create_team(name, token):
    response = api_post("/teams", data={"name": name}, token=token)
    return response

def fetch_teams_for_user(user_id: str) -> List[Dict[str, Any]]:
    response = api_get(f"/teams?user_id={user_id}")
    return response

def create_playlist(video_data, token, name, playlist_id):
    response = api_post("/playlists", data={"name": name, "playlist_id": playlist_id}, token=token)
    #TODO: combine all these individual API calls to a single call
    create_video(video_data, token, name)
    #TODO: please do error handling

def create_video(video_data, token, name):
    for video in video_data:
        response = api_post(f"/playlists/{name}/videos", data=video, token=token)

def load_playlists() -> List[Dict[str, Any]]:
    cache_key = "playlists"
    cached = cache_get(cache_key)
    if cached:
        return cached
    data = api_get("/playlists")
    cache_set(cache_key, data)
    return data

def load_playlists_for_user(user_id: str, filter: str = "all") -> List[Dict[str, Any]]:
    cache_key = f"playlists_user_{user_id}_{filter}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    data = api_get(f"/playlists?user_id={user_id}&filter={filter}")
    cache_set(cache_key, data)
    return data

def format_duration(seconds: int) -> str:
    """Convert seconds into a human-readable format (HH:MM:SS or MM:SS)."""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"  # HH:MM:SS
    return f"{int(minutes):02}:{int(seconds):02}"  # MM:SS

def load_videos(playlist_id: Optional[str] = None, response_dict=False) -> List[Dict[str, Any]]:
    cache_key = f"videos_{playlist_id or 'all'}"
    cached = cache_get(cache_key)
    if cached:
        videos = cached
    else:
        playlists = load_playlists()
        videos = []
        for playlist in playlists:
            if playlist_id is None or playlist.get("_id") == playlist_id:
                for video in playlist.get("videos", []):
                    video["playlist_id"] = playlist.get("_id")
                    video["playlist_name"] = playlist.get("name")
                    video["duration_human"] = format_duration(video.get("duration_seconds", 0))
                    videos.append(video)
        videos.sort(key=lambda x: x.get("date", ""), reverse=True)
        cache_set(cache_key, videos)
    if response_dict:
        return {video["video_id"]: video for video in videos if "video_id" in video}
    return videos

def load_video(video_id):
    cache_key = f"video_{video_id}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    videos = load_videos(response_dict=True)
    video = videos.get(video_id)
    if video:
        cache_set(cache_key, video)
    return video

def get_playlist_id_for_video(video_id: str) -> Optional[str]:
    playlists = load_playlists()
    for playlist in playlists:
        for video in playlist.get("videos", []):
            
            if video.get("video_id") == video_id:
                return playlist.get("name") ##Fix
    return None

def load_clips(video_id: str) -> List[Dict[str, Any]]:
    playlist_id = get_playlist_id_for_video(video_id)
    if not playlist_id:
        raise ValueError(f"Video with id {video_id} not found in any playlist.")
    playlists = load_playlists()
    for playlist in playlists:
        if playlist.get("name") == playlist_id:
            for video in playlist.get("videos", []):
                if video.get("video_id") == video_id:
                    return video.get("clips", [])
    return []

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
            lines.append(" ".join(f"#{l}" for l in video_metadata["labels"]))
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
            ""
        ]

    if not has_clips and duration:
        lines.append("00:00 - 00:30 | Clip Title Here | Optional description here @partner1 @partner2 #label1 #label2")
        clips = [{
            "start": 0,
            "end": duration,
            "type": "autogen"
        }]

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
        labels = " ".join(f"#{l}" for l in clip.get("labels", []))
        full_desc = " ".join(part for part in [description, partners, labels] if part)

        lines.append(f"{format_time(start)} - {format_time(end)} | {title} | {full_desc}")

    return "\n".join(lines)


def parse_clip_line(line: str) -> Optional[Dict[str, Any]]:
    try:
        if "Clip Title Here" in line or "@autogen" in line:
            return None

        import re
        match = re.match(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s*\|\s*([^|]+)\s*(?:\|\s*(.*))?', line)
        if not match:
            return None
        start_str, end_str, title, full_desc = match.groups()

        def to_seconds(t: str) -> int:
            minutes, seconds = map(int, t.strip().split(":"))
            return minutes * 60 + seconds

        full_desc = full_desc or ""
        partners = re.findall(r'@(\w+)', full_desc)
        labels = re.findall(r'#(\w+)', full_desc)
        description = re.sub(r'[@#]\w+', '', full_desc).strip()

        return {
            "start": to_seconds(start_str),
            "end": to_seconds(end_str),
            "title": title.strip(),
            "description": description,
            "type": "clip",
            "partners": partners,
            "labels": labels
        }
    except Exception:
        return None

def parse_raw_text(raw_text: str) -> Dict[str, Any]:
    video_data = {
        "partners": [],
        "labels": [],
        "type": "",
        "notes": "",
        "clips": [],
        "youtube_url": "",
        "date": "",
        "title": "",
        "duration_seconds": 0.0
    }

    for line in raw_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        tokens = line.split()
        if all(token.startswith('@') or token.startswith('#') for token in tokens):
            for token in tokens:
                if token.startswith("@"):
                    video_data["partners"].append(token[1:].strip())
                elif token.startswith("#"):
                    video_data["labels"].append(token[1:].strip())
        elif line.lower().startswith("type:"):
            video_data["type"] = line.split(":", 1)[1].strip()
        elif line.lower().startswith("notes:"):
            video_data["notes"] = line.split(":", 1)[1].strip()
        elif re.match(r'\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}', line):
            clip = parse_clip_line(line)
            if clip:
                video_data["clips"].append(clip)

    return video_data

def save_video_data_clips(video_data: Dict[str, Any], token) -> bool:
    playlist_name = get_playlist_id_for_video(video_data.get("video_id"))
    if not playlist_name:
        print(f"Could not find playlist for video_id: {video_data.get('video_id')}")
        return False

    try:
        api_put(f"/playlists/{playlist_name}/videos", data=video_data, token=token)
        return True
    except requests.HTTPError as e:
        print(f"Failed to save video data: {e}")
        return False
       #TODO: if not successful, display reason in ui?

def parse_and_save_clips(video_id: str, raw_text: str, token):
    video_data = parse_raw_text(raw_text)
    video_data["video_id"] = video_id
    return save_video_data_clips(video_data, token)

def get_all_partners() -> List[str]:
    partners_set = set()
    videos = load_videos()

    for video in videos:
        video_partners = video.get("partners", [])
        partners_set.update(video_partners)

        clips = video.get("clips", [])
        for clip in clips:
            if clip.get("type") == "clip":
                partners_set.update(clip.get("partners", []))

    return sorted(partners_set)

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
                    "labels": merged_labels
                }
                result.append(combined)
    return result

def add_clip_to_video(playlist_name: str, video_id: str, clip: dict, token: str):
    """Add a single clip to a video in a playlist."""
    endpoint = f"/playlists/{playlist_name}/videos/{video_id}/clips"
    return api_post(endpoint, data=clip, token=token)

def update_clip_in_video(playlist_name: str, video_id: str, clip: dict, token: str):
    """Update a single clip in a video in a playlist."""
    endpoint = f"/playlists/{playlist_name}/videos/{video_id}/clips"
    return api_put(endpoint, data=clip, token=token)

def convert_video_metadata_to_raw_text(video: dict) -> str:
    partners_line = " ".join(f"@{p}" for p in video.get("partners", []))
    labels_line = " ".join(f"#{l}" for l in video.get("labels", []))
    notes = video.get("notes", "")
    return "\n".join(filter(None, [partners_line, labels_line, notes]))

def save_video_metadata(video_metadata: dict, token: str) -> bool:
    playlist_name = get_playlist_id_for_video(video_metadata.get("video_id"))
    if not playlist_name:
        print(f"Could not find playlist for video_id: {video_metadata.get('video_id')}")
        return False
    try:
        # import pdb; pdb.set_trace()
        api_put(f"/playlists/{playlist_name}/videos", data=video_metadata, token=token)
        return True
    except Exception as e:
        print(f"Failed to save video metadata: {e}")
        return False

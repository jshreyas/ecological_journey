import asyncio
import os
from collections import defaultdict

import httpx
import requests
from dotenv import load_dotenv

from ui.data.crud import create_service_token
from ui.data.models import User
from ui.utils.youtube import fetch_videos_metadata

load_dotenv()

API_BASE = os.environ.get("BASE_URL_SHARE")

service_user = User.find_one(User.role == "service").run()
if not service_user:
    raise RuntimeError("Service user not found")

token = create_service_token(service_user)


def get_playlists():
    r = requests.get(f"{API_BASE}/api/playlists")
    r.raise_for_status()
    return r.json()


async def check_playable_videos(video_ids: list[str]) -> set[str]:
    if not video_ids:
        return set()

    unique_ids = list(dict.fromkeys(video_ids))

    async with httpx.AsyncClient() as client:
        metadata = await fetch_videos_metadata(client, unique_ids)

    return set(metadata.keys())


def delete_inactive_videos(playlist_id: str, video_ids: list[str]):
    if not video_ids:
        return
    r = requests.delete(
        f"{API_BASE}/api/playlists/{playlist_id}/videos",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"video_ids": video_ids},
        timeout=30,
    )
    r.raise_for_status()
    print(f"🗑️ Removed {len(video_ids)} inactive video(s) from playlist {playlist_id}")


def main():
    playlists = get_playlists()
    per_playlist_ids: dict[str, list[str]] = defaultdict(list)
    all_video_ids: list[str] = []

    for playlist in playlists:
        playlist_id = playlist["_id"]
        videos = playlist.get("videos", [])
        playlist_video_ids = [v["video_id"] for v in videos if v.get("video_id")]

        if playlist_video_ids:
            per_playlist_ids[playlist_id] = playlist_video_ids
            all_video_ids.extend(playlist_video_ids)

    playable_ids = asyncio.run(check_playable_videos(all_video_ids))

    for playlist in playlists:
        playlist_id = playlist["_id"]
        video_ids = per_playlist_ids.get(playlist_id, [])
        inactive_ids = [video_id for video_id in video_ids if video_id not in playable_ids]
        if inactive_ids:
            print(f"Playlist {playlist['name']} has {len(inactive_ids)} inactive video(s): \n{inactive_ids}")
            delete_inactive_videos(playlist_id, inactive_ids)


if __name__ == "__main__":
    main()

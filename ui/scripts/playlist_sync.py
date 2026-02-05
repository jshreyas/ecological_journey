import asyncio
import os

import requests
from dotenv import load_dotenv

from ui.utils.youtube import fetch_playlist_items

load_dotenv()

API_BASE = os.environ["APP_API_BASE"]
SERVICE_TOKEN = os.environ["SERVICE_TOKEN"]
YOUTUBE_API_KEY = os.environ["API_KEY"]

HEADERS = {
    "Authorization": f"Bearer {SERVICE_TOKEN}",
}


def get_playlists():
    r = requests.get(f"{API_BASE}/api/playlists")
    r.raise_for_status()

    response = []

    for p in r.json():
        videos = p.get("videos", [])

        if videos:
            latest_saved_date = max(v["date"] for v in videos)
            existing_video_ids = [v["video_id"] for v in videos if "video_id" in v]
        else:
            latest_saved_date = None
            existing_video_ids = []

        response.append(
            {
                "_id": p["_id"],
                "name": p["name"],
                "playlist_id": p["playlist_id"],  # YouTube playlist ID
                "latest_saved_date": latest_saved_date,
                "existing_video_ids": existing_video_ids,
            }
        )

    return response


def post_new_videos(playlist_id, videos):
    if not videos:
        return

    print(f"Would sync {len(videos)} videos for playlist {playlist_id}")
    # stubbed for now
    # requests.post(...)


def main():
    playlists = get_playlists()

    _ = asyncio.run(
        fetch_playlist_items(
            playlists,
            api_key=YOUTUBE_API_KEY,
            concurrency=5,
        )
    )

    # for playlist_id, videos in _.items():
    #     post_new_videos(playlist_id, videos)


if __name__ == "__main__":
    main()

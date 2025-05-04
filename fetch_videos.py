import os
import json
import re
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
PLAYLIST_ID = "PLHXvJ_QLQWhXuOo2HcwsL4sysM79x8Id8"
BASE_URL = "https://www.googleapis.com/youtube/v3"
FETCH_VIDEOS_COUNT = None

def fetch_playlist_items(count=None):
    videos = []
    next_page_token = ""
    while True:
        url = f"{BASE_URL}/playlistItems?part=snippet&maxResults=50&playlistId={PLAYLIST_ID}&key={API_KEY}&pageToken={next_page_token}"
        res = requests.get(url)
        data = res.json()
        for item in data["items"]:
            if count and len(videos) >= count:
                return videos
            snippet = item["snippet"]
            video_id = snippet["resourceId"]["videoId"]
            video_data = {
                "title": snippet["title"],
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "description": snippet.get("description", ""),
                "published_at": snippet["publishedAt"]
            }
            videos.append(video_data)
        if "nextPageToken" in data and (not count or len(videos) < count):
            next_page_token = data["nextPageToken"]
        else:
            break
    return videos


def parse_description(desc):
    def extract(pattern):
        match = re.search(pattern, desc, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    return {
        "partner": extract(r"Partner:\s*(.+)"),
        "type": extract(r"Type:\s*(.+)"),
        "positions": [p.strip() for p in extract(r"Positions:\s*(.+)").split(",") if p.strip()],
        "notes": extract(r"Notes:\s*(.+)")
    }

def main():
    raw_videos = fetch_playlist_items(count=FETCH_VIDEOS_COUNT)
    parsed_videos = []
    for v in raw_videos:
        meta = parse_description(v["description"])
        parsed_videos.append({
            "title": v["title"],
            "video_id": v["video_id"],
            "youtube_url": v["url"],
            "date": v["published_at"],
            **meta
        })

    with open("fetch_videos.json", "w") as f:
        json.dump(parsed_videos, f, indent=2)

    print(f"Saved {len(parsed_videos)} videos to fetch_videos.json")

if __name__ == "__main__":
    main()

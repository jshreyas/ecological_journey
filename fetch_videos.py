import os
import json
import re
import requests  # type: ignore
from dotenv import load_dotenv  # type: ignore
from datetime import datetime, time
import pytz  # type: ignore

# Load API key from environment
load_dotenv()
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("Missing API_KEY in environment variables")

PLAYLIST_ID = "PLHXvJ_QLQWhXuOo2HcwsL4sysM79x8Id8"
BASE_URL = "https://www.googleapis.com/youtube/v3"
FETCH_VIDEOS_COUNT = None  # Set to an integer to limit fetched items

pst = pytz.timezone("America/Los_Angeles")

def fetch_video_upload_date(video_id):
    """Fetch actual upload date of the video from YouTube Data API."""
    url = f"{BASE_URL}/videos?part=snippet&id={video_id}&key={API_KEY}"
    response = requests.get(url)
    if not response.ok:
        return None

    try:
        published_utc = datetime.strptime(
            response.json()['items'][0]['snippet']['publishedAt'],
            "%Y-%m-%dT%H:%M:%SZ"
        )
        return published_utc.replace(tzinfo=pytz.utc).astimezone(pst).date()
    except (IndexError, KeyError, ValueError):
        return None

def check_update_date_title_mismatch(video):
    title = video["title"]
    published_at = video["published_at"]

    date_formats = [
        ("%Y-%m-%d", r"\b(\d{4}-\d{2}-\d{2})\b"),
        ("%d-%m-%Y", r"\b(\d{2}-\d{2}-\d{4})\b"),
        ("%B %d, %Y", r"\b([A-Za-z]+ \d{1,2}, \d{4})\b"),
    ]

    for fmt, pattern in date_formats:
        match = re.search(pattern, title)
        if match:
            title_date_str = match.group(1)
            try:
                title_date = datetime.strptime(title_date_str, fmt).date()
                published_utc = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
                published_pst_date = pytz.utc.localize(published_utc).astimezone(pst).date()

                if title_date != published_pst_date:
                    actual_upload_date = fetch_video_upload_date(video["video_id"])
                    if actual_upload_date:
                        new_utc = pst.localize(datetime.combine(actual_upload_date, time.min)).astimezone(pytz.utc)
                        video["published_at"] = new_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                pass
            break

    return video

def fetch_playlist_items(count=None):
    videos = []
    next_page_token = ""

    while True:
        url = f"{BASE_URL}/playlistItems?part=snippet&maxResults=50&playlistId={PLAYLIST_ID}&key={API_KEY}&pageToken={next_page_token}"
        response = requests.get(url)
        if not response.ok:
            break

        data = response.json()
        for item in data.get("items", []):
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
            video_data = check_update_date_title_mismatch(video_data)
            videos.append(video_data)

        next_page_token = data.get("nextPageToken", "")
        if not next_page_token or (count and len(videos) >= count):
            break

    return videos

def parse_description(desc):
    def extract(pattern):
        match = re.search(pattern, desc, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    return {
        "partners": [p.strip() for p in extract(r"Partners:\s*(.+)").split(",") if p.strip()],
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

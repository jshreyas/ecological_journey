# fetch_videos.py
import os
import json
import re
import requests
from dotenv import load_dotenv
from datetime import datetime, time
import pytz
import isodate

# Load API key from environment
load_dotenv()
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("Missing API_KEY in environment variables")

PLAYLIST_ID = "PLHXvJ_QLQWhXuOo2HcwsL4sysM79x8Id8" # Grappling Journal
PLAYLIST_ID = "PLHXvJ_QLQWhWfwGejBdQE8LjHHToMMCge" # Home Training Journal
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

def fetch_video_duration(video_id):
    """Fetch video duration (in seconds) from YouTube Data API."""
    url = f"{BASE_URL}/videos?part=contentDetails&id={video_id}&key={API_KEY}"
    response = requests.get(url)
    if not response.ok:
        return None

    try:
        duration_str = response.json()['items'][0]['contentDetails']['duration']
        # Convert ISO 8601 duration string to total seconds
        video_duration = isodate.parse_duration(duration_str).total_seconds()
        return video_duration
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

def fetch_playlist_items(playlist_id=PLAYLIST_ID, count=None):
    videos = []
    next_page_token = ""

    while True:
        url = f"{BASE_URL}/playlistItems?part=snippet&maxResults=50&playlistId={playlist_id}&key={API_KEY}&pageToken={next_page_token}"
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
                # "description": snippet.get("description", ""), ## TODO: do we need this?
                "published_at": snippet["publishedAt"]
            }

            # Fetch video duration and add it to the video data
            video_duration = fetch_video_duration(video_id)
            if video_duration:
                video_data["duration_seconds"] = video_duration

            video_data = check_update_date_title_mismatch(video_data)
            videos.append(video_data)

        next_page_token = data.get("nextPageToken", "")
        if not next_page_token or (count and len(videos) >= count):
            break

    return videos

def check_create_playlist_db(playlist_id):
    API_URL = os.getenv("FASTAPI_API_URL", "http://localhost:8000")  # Or prod URL
    AUTH_TOKEN = os.getenv("JWT_TOKEN")  # Optional

    headers = {"Content-Type": "application/json"}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

    response = requests.get(f"{API_URL}/playlists", headers=headers)
    playlist_exists = False
    for each in response.json():
        if each["name"] == playlist_id:
            playlist_exists = True
    if not playlist_exists:
        playlist = {
            "name": playlist_id,
            "videos": []
        }
        response = requests.post(f"{API_URL}/playlists", headers=headers, json=playlist)
        if not response.ok:
            print(f"Failed to create playlist: {playlist_id}: {response.text}")
        else:
            print(f"Created {playlist_id} successfully")

def upload_to_fastapi(playlist_id, video):
    API_URL = os.getenv("FASTAPI_API_URL", "http://localhost:8000")  # Or prod URL
    AUTH_TOKEN = os.getenv("JWT_TOKEN")  # Optional

    headers = {"Content-Type": "application/json"}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

    url = f"{API_URL}/playlists/{playlist_id}/videos"
    response = requests.post(url, headers=headers, json=video)

    if not response.ok:
        print(f"Failed to upload video {video['video_id']}: {response.text}")
    else:
        print(f"Uploaded {video['video_id']}")


def main():
    print("this script does nothing at the moment")
    pass

if __name__ == "__main__":
    main()

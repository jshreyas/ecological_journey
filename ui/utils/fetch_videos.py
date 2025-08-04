# fetch_videos.py
import os
import re
from datetime import datetime, time

import isodate
import pytz
import requests
from dotenv import load_dotenv
from log import log

# Load API key from environment
load_dotenv()
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("Missing API_KEY in environment variables")

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
        published_utc = datetime.strptime(response.json()["items"][0]["snippet"]["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")
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
        duration_str = response.json()["items"][0]["contentDetails"]["duration"]
        # Convert ISO 8601 duration string to total seconds
        video_duration = isodate.parse_duration(duration_str).total_seconds()
        return video_duration
    except (IndexError, KeyError, ValueError) as e:
        log.error(f"Error fetching duration for video {video_id}: {e}")
        return None


def check_update_date_title_mismatch(video):
    title = video["title"]
    published_at = video["date"]

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
                        video["date"] = new_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                pass
            break

    return video


def fetch_playlist_metadata(playlist_id):
    url = f"{BASE_URL}/playlists?part=snippet&id={playlist_id}&key={API_KEY}"
    response = requests.get(url)
    if not response.ok:
        return None

    data = response.json()
    if "items" in data and len(data["items"]) > 0:
        return data["items"][0]["snippet"]
    else:
        return None


def fetch_playlist_items(playlist_id, latest_saved_date=None, count=None):
    videos = []
    next_page_token = ""

    while True:
        url = f"{BASE_URL}/playlistItems?part=snippet&maxResults=50&playlistId={playlist_id}&key={API_KEY}&pageToken={next_page_token}"
        response = requests.get(url)
        if not response.ok:
            break

        data = response.json()
        for item in data.get("items", []):
            snippet = item["snippet"]
            published_at = snippet["publishedAt"]
            published_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))

            if latest_saved_date and published_dt < latest_saved_date:
                # Stop fetching as we've reached already-synced videos
                return videos

            if count and len(videos) >= count:
                return videos

            video_id = snippet["resourceId"]["videoId"]
            video_data = {
                "title": snippet["title"],
                "video_id": video_id,
                "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
                "date": published_at,
                "type": "",
                "partners": [],
                "positions": [],
                "notes": "",
                "labels": [],
                "clips": [],
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

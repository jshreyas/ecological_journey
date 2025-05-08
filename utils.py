import json
import os
import requests


CLIPS_DIR = "data/clips"
VIDEOS_DIR = "data/videos"
GRAPPLING_JSON_FILE = "fetch_videos.json"
HOME_TRAINING_JSON_FILE = "home_training.json"

def load_grappling_videos():
    with open(os.path.join(VIDEOS_DIR, GRAPPLING_JSON_FILE)) as f:
        return json.load(f)
    
def load_home_training_videos():
    with open(os.path.join(VIDEOS_DIR, HOME_TRAINING_JSON_FILE)) as f:
        return json.load(f)

def load_videos():
    return load_home_training_videos() + load_grappling_videos()

def load_clips(video_id):
    file_path = os.path.join(CLIPS_DIR, f"{video_id}.json")
    if os.path.exists(file_path):
        with open(file_path) as f:
            return json.load(f)
    return []

def save_clips(video_id, clips):
    file_path = os.path.join(CLIPS_DIR, f"{video_id}.json")
    with open(file_path, "w") as f:
        json.dump(clips, f, indent=2)

# TODO: update the video embed window based on the orientation
def get_video_orientation_internal(video_id: str) -> str:
    url = "https://www.youtube.com/youtubei/v1/player"
    params = {
        "videoId": video_id
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.youtube.com"
    }
    payload = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20210721.00.00"
            }
        },
        "videoId": video_id
    }

    response = requests.post(url, params=params, json=payload, headers=headers)
    data = response.json()

    try:
        streaming_data = data.get("streamingData", {})
        formats = streaming_data.get("formats", [])

        # Get the first video format that includes width & height
        for fmt in formats:
            width = fmt.get("width")
            height = fmt.get("height")
            if width and height:
                return "portrait" if height > width else "landscape"

        return "Unknown (no resolution data found)"
    except Exception as e:
        return f"Error: {str(e)}"
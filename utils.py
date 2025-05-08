import json
import os


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

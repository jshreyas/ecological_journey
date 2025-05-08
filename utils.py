import json


GRAPPLING_JSON_FILE = "fetch_videos.json"
HOME_TRAINING_JSON_FILE = "home_training.json"

def load_grappling_videos():
    with open(GRAPPLING_JSON_FILE) as f:
        return json.load(f)
    
def load_home_training_videos():
    with open(HOME_TRAINING_JSON_FILE) as f:
        return json.load(f)

def load_videos():
    return load_home_training_videos() + load_grappling_videos()
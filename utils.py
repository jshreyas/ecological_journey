import json
import os
import re
import requests # type: ignore
import streamlit.components.v1 as components # type: ignore


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

def save_video_metadata(video_id, updated_metadata):
    file_path = os.path.join(VIDEOS_DIR, GRAPPLING_JSON_FILE) #TODO: this doesnt work for hometraining videos

    # Load all videos
    with open(file_path, "r", encoding="utf-8") as f:
        videos = json.load(f)

    # Update matching video
    updated = False
    for video in videos:
        if video.get("video_id") == video_id:
            video.update(updated_metadata)
            updated = True
            break

    if not updated:
        raise ValueError(f"Video with ID '{video_id}' not found.")

    # Save back
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)


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

def format_time(seconds):
    minutes = seconds // 60
    sec = seconds % 60
    return f"{int(minutes):02}:{int(sec):02}"

def parse_clip_line(line):
    try:
        # Ignore instructional header or autogen clip
        if "Clip Title Here" in line or "@autogen" in line:
            return None

        match = re.match(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s*\|\s*([^|]+)\s*(?:\|\s*(.*))?', line)
        if not match:
            return None
        start_str, end_str, title, full_desc = match.groups()

        def to_seconds(t):
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

def parse_raw_text(raw_text):
    clips = []
    video_metadata = {
        "partners": [],
        "positions": [],
        "type": "",
        "notes": ""
    }

    for line in raw_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        # Video-level metadata parsing
        if re.match(r'^@[\w\s@#]*$', line):  # Only @ and # tokens
            tokens = line.split()
            for token in tokens:
                if token.startswith("@"):
                    video_metadata["partners"].append(token[1:].strip())
                elif token.startswith("#"):
                    video_metadata["positions"].append(token[1:].strip())
        elif line.lower().startswith("type:"):
            video_metadata["type"] = line.split(":", 1)[1].strip()
        elif line.lower().startswith("notes:"):
            video_metadata["notes"] = line.split(":", 1)[1].strip()

        # Clip line
        elif re.match(r'\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}', line):
            clip = parse_clip_line(line)
            if clip:
                clips.append(clip)

        # Ignore anything else silently
    return clips, video_metadata

def parse_and_save_clips(video_id, raw_text):
    clips, video_meta = parse_raw_text(raw_text)
    
    # Save segment clips
    save_clips(video_id, clips)

    # Save updated video metadata
    if video_meta:
        save_video_metadata(video_id, video_meta)

def convert_clips_to_raw_text(video_id, video_duration=None):
    clips = load_clips(video_id)
    videos = load_videos()
    video_metadata = next((v for v in videos if v["video_id"] == video_id), {})

    lines = []

    # Determine if video-level metadata exists
    has_metadata = any(video_metadata.get(k) for k in ["partners", "positions", "type", "notes"])
    has_clips = bool(clips)

    # Scenario 1, 2, 3, or 4
    if has_metadata:
        if video_metadata.get("partners"):
            lines.append(" ".join(f"@{p}" for p in video_metadata["partners"]))
        if video_metadata.get("positions"):
            lines.append(" ".join(f"#{pos}" for pos in video_metadata["positions"]))
        if video_metadata.get("type"):
            lines.append(f"type: {video_metadata['type']}")
        if video_metadata.get("notes"):
            lines.append(f"notes: {video_metadata['notes']}")
        lines.append("")  # spacer
    elif not has_metadata:
        # Insert placeholder metadata
        lines.append("@partner1 @partner2 #position1 #position2")
        lines.append("type: positional/sparring/rolling/instructional")
        lines.append("notes: optional general notes about this video")
        lines.append("")  # spacer

    # Scenario 1 or 3 (no clips)
    if not has_clips and video_duration is not None:
        lines.append("00:00 - 00:30 | Clip Title Here | Optional description here @partner1 @partner2 #label1 #label2")
        clips = [{
            "start": 0,
            "end": video_duration,
            "type": "autogen"
        }]

    # Scenarios 2 and 4 (render actual clips)
    for clip in clips:
        start = clip.get("start", 0)
        end = clip.get("end", 0)

        if not video_duration:
            video_duration = video_metadata.get("duration_seconds", None)
        if video_duration and end > video_duration:
            end = video_duration

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


def find_clips_by_partner(partner):
    result = []
    videos = load_videos()  # video-level metadata
    video_meta_lookup = {v["video_id"]: v for v in videos}

    for filename in os.listdir(CLIPS_DIR):
        if not filename.endswith(".json"):
            continue
        video_id = filename.removesuffix(".json")
        filepath = os.path.join(CLIPS_DIR, filename)

        video_meta = video_meta_lookup.get(video_id, {})
        video_partners = video_meta.get("partners", [])

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                clips = json.load(f)
                for clip in clips:
                    clip_partners = clip.get("partners", [])
                    if partner in clip_partners or partner in video_partners:
                        result.append({
                            "video_id": video_id,
                            **video_meta,
                            **clip
                        })
        except Exception as e:
            print(f"Error reading {filepath}: {e}")

    return result

def get_all_partners():
    partners_set = set()
    videos = load_videos()  # load once

    for filename in os.listdir(CLIPS_DIR):
        if not filename.endswith(".json"):
            continue
        video_id = filename.removesuffix(".json")
        filepath = os.path.join(CLIPS_DIR, filename)

        # Add video-level partners
        video_meta = next((v for v in videos if v["video_id"] == video_id), {})
        video_partners = video_meta.get("partners", [])
        partners_set.update(video_partners)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                clips = json.load(f)
                for clip in clips:
                    if clip.get("type") == "clip":
                        partners_set.update(clip.get("partners", []))
        except Exception as e:
            print(f"Error reading {filepath}: {e}")

    return sorted(partners_set)


def embed_youtube_player(video_id, start, end, speed):
    end_js = f"{end}" if end else "null"
    html_code = f"""
    <div id="player"></div>
    <script>
      // Load the YouTube iframe API once
      if (!window.YT) {{
        var tag = document.createElement('script');
        tag.src = "https://www.youtube.com/iframe_api";
        var firstScriptTag = document.getElementsByTagName('script')[0];
        firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
      }}

      // Wait for the API to be ready
      function createPlayer() {{
        player = new YT.Player('player', {{
          height: '360',
          width: '100%',
          videoId: '{video_id}',
          playerVars: {{
            'rel': 0,
            'modestbranding': 1
          }},
          events: {{
            'onReady': function(event) {{
              player.seekTo({start}, true);
              player.setPlaybackRate({speed});
              player.playVideo();

              if ({end_js}) {{
                const stopInterval = setInterval(() => {{
                  if (player.getCurrentTime() >= {end_js}) {{
                    player.pauseVideo();
                    clearInterval(stopInterval);
                  }}
                }}, 200);
              }}
            }}
          }}
        }});
      }}

      // Attach to global scope so API can find it
      window.onYouTubeIframeAPIReady = function() {{
        createPlayer();
      }};

      // If API is already loaded, call directly
      if (window.YT && window.YT.Player) {{
        createPlayer();
      }}
    </script>
    """
    components.html(html_code, height=400)

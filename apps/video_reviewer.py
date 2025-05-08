# apps/video_reviewer.py
import streamlit as st
import json
import math
import os
import re
import streamlit.components.v1 as components
from hydralit import HydraHeadApp


# Constants
SEGMENTS_FILE = "segments.json"
VIDEO_ID = "i41wadv6nBg"  # Replace with your actual video ID

SEGMENT_ICONS = {
    "intro": ("📘", "#D6EAF8"),
    "warm": ("🔥", "#F9E79F"),
    "concept": ("🧠", "#D5F5E3"),
    "demo": ("🎬", "#FADBD8"),
    "q&a": ("❓", "#E8DAEF"),
    "outro": ("🏋️", "#D7DBDD"),
    "default": ("🔹", "#E5E8E8"),
    "skip": ("🚫", "#F5B7B1"),
}

def parse_clip_line(line):
    try:
        time_pattern = r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})'
        match = re.match(f"{time_pattern}\s*\|\s*(.*?)\s*\|\s*(.*)", line)
        if not match:
            return None
        start_str, end_str, title, description = match.groups()

        def to_seconds(t):
            minutes, seconds = map(int, t.strip().split(":"))
            return minutes * 60 + seconds

        return {
            "start": to_seconds(start_str),
            "end": to_seconds(end_str),
            "title": title.strip(),
            "description": description.strip(),
            "type": "clip"
        }
    except Exception as e:
        return None

# Load and save segments
def load_segments():
    if os.path.exists(SEGMENTS_FILE):
        with open(SEGMENTS_FILE, "r") as f:
            return json.load(f)
    return []

def save_segments(segments):
    with open(SEGMENTS_FILE, "w") as f:
        json.dump(segments, f, indent=2)

# Embed a single YouTube player with start/end/speed
def embed_youtube_player(start, end, speed):
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
          videoId: '{VIDEO_ID}',
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

# --- Utility Functions ---
def format_time(seconds):
    minutes = seconds // 60
    sec = seconds % 60
    return f"{int(minutes):02}:{int(sec):02}"

def convert_clips_to_raw_text(clips):
    lines = []
    for clip in clips:
        if clip.get("type") != "clip":
            continue
        start = format_time(clip["start"])
        end = format_time(clip["end"])
        title = clip.get("title", "")
        description = clip.get("description", "")
        lines.append(f"{start} - {end} | {title} | {description}")
    return "\n".join(lines)


class VRApp(HydraHeadApp):

    def run(self):

        col11, col12 = st.columns([11, 1])
        with col11:
            st.title("🎞️ Video Reviewer")
        with col12:
            layout_ratio = st.selectbox("", ["3:1", "2:1", "1:1", "1:2", "1:3"])
        ratios = {"3:1": [3,1], "2:1": [2,1], "1:1": [1,1], "1:2": [1,2], "1:3": [1,3]}
        # Radio sizable Layout: Video | Clipper
        col1, col2 = st.columns(ratios[layout_ratio])

        segments = load_segments()

        # Default state
        if "selected_segment_idx" not in st.session_state:
            st.session_state.selected_segment_idx = 0
        if "playback_speed" not in st.session_state:
            st.session_state.playback_speed = 1.0

        # --- Main Video Player (Col1) ---
        with col1:
            if segments:
                seg = segments[st.session_state.selected_segment_idx]
                start = seg.get("start", 0)
                end = seg.get("end", 0)
                speed = st.session_state.playback_speed

                with st.container():
                    # Embed video player
                    embed_youtube_player(start, end, speed)

                new_speed = st.slider(
                    label="",
                    min_value=0.25,
                    max_value=2.0,
                    value=st.session_state.playback_speed,
                    step=0.25,
                    key="playback_speed",
                    label_visibility="collapsed"
                )

                # Manual rerun if changed
                if new_speed != st.session_state.playback_speed:
                    st.session_state.playback_speed = new_speed
                    st.rerun()

            else:
                st.warning(f"No segments found in {SEGMENTS_FILE}!")

        # --- Clipper (Col2) ---
        with col2:
            with st.form("clipper"):

                # Load existing segments (for editing)
                try:
                    with open(SEGMENTS_FILE, "r") as f:
                        segments = json.load(f)
                except FileNotFoundError:
                    segments = []

                # Convert segments to raw text format
                raw_text = convert_clips_to_raw_text(segments)
                
                updated_raw_text = st.text_area("✏️ Clipper", value=raw_text, height=400)

                # Save Changes Button
                submit = st.form_submit_button("💾 Save Changes")
                if submit:
                    try:
                        # Convert updated raw text back to segments
                        clip_lines = updated_raw_text.strip().split("\n")
                        new_clips = [parse_clip_line(line) for line in clip_lines if parse_clip_line(line)]

                        # Save to SEGMENTS_FILE
                        with open(SEGMENTS_FILE, "w") as f:
                            json.dump(new_clips, f, indent=4)

                        st.success("✅ Raw Text saved successfully!")
                    except Exception as e:
                        st.error(f"Error: {e}")

        st.markdown("## 🎞️ Clipboard")

        # --- Clipboard Interface ---
        clip_container = st.container()
        with clip_container:

            # Customize number of columns based on screen size or fixed value
            NUM_COLUMNS = 3

            clip_buttons = [seg for seg in segments if seg["type"] == "clip"]
            num_rows = math.ceil(len(clip_buttons) / NUM_COLUMNS)

            for row in range(num_rows):
                cols = st.columns(NUM_COLUMNS)
                for col_idx in range(NUM_COLUMNS):
                    i = row * NUM_COLUMNS + col_idx
                    if i < len(clip_buttons):
                        seg = clip_buttons[i]
                        key = next((k for k in SEGMENT_ICONS if k in seg.get('title', '').lower()), "default")
                        emoji, _ = SEGMENT_ICONS[key]

                        is_selected = i == st.session_state.selected_segment_idx
                        highlight_style = "**" if is_selected else ""
                        label = f"{highlight_style}{emoji} {seg['title']} ({format_time(seg['start'])} → {format_time(seg['end'])}){highlight_style}"

                        if cols[col_idx].button(label, key=f"clip_{i}"):
                            st.session_state.selected_segment_idx = i
                            st.rerun()



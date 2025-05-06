import streamlit as st
import json
import os
import streamlit.components.v1 as components

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


# Utility function for human-readable time
def format_time(seconds):
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02}:{m:02}:{s:02}"
    else:
        return f"{m:02}:{s:02}"

# --- UI Layout ---
st.set_page_config(layout="wide")
st.title("🎞️ Video Segment Navigator")

segments = load_segments()

# Default state
if "selected_segment_idx" not in st.session_state:
    st.session_state.selected_segment_idx = 0
if "playback_speed" not in st.session_state:
    st.session_state.playback_speed = 1.0

# Layout: Video | Segment Navigation
col1, col2 = st.columns([3, 1])

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

        # Unified, low-footprint speed slider just below video
        slider_cols = st.columns([1, 5])
        with slider_cols[0]:
            st.caption("⏩ Speed")
        with slider_cols[1]:
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
        st.warning("No segments found in segments.json!")

# --- Segment List (Col2) ---
with col2:
    # Use tabs for Chapters, Clips, and Skipped
    tab_chapters, tab_clips, tab_skipped = st.tabs(["📘 Chapters", "🎞️ Clips", "🚫 Skipped"])

    # Chapter List
    with tab_chapters:
        chapter_container = st.container()
        with chapter_container:
            for i, seg in enumerate(segments):
                if seg['type'] != 'chapter' or seg.get('skip', False):
                    continue
                key = next((k for k in SEGMENT_ICONS if k in seg.get('title', '').lower()), "default")
                emoji, _ = SEGMENT_ICONS[key]
                start_str = format_time(seg['start'])
                end_str = f" → {format_time(seg['end'])}" if seg.get('end') else ""

                is_selected = i == st.session_state.selected_segment_idx
                highlight_style = "**" if is_selected else ""
                label = f"{highlight_style}{emoji} {seg['title']} ({start_str}{end_str}){highlight_style}"

                if st.button(label, key=f"chapter_{i}"):
                    st.session_state.selected_segment_idx = i
                    st.rerun()

        if len(segments) > 5:
            chapter_container.markdown(
                f"""
                <style>
                    .stContainer {{
                        max-height: 300px;
                        overflow-y: auto;
                    }}
                </style>
                """, unsafe_allow_html=True
            )

    # Clip List
    with tab_clips:
        clip_container = st.container()
        with clip_container:
            for i, seg in enumerate(segments):
                if seg['type'] != 'clip':
                    continue
                key = next((k for k in SEGMENT_ICONS if k in seg.get('title', '').lower()), "default")
                emoji, _ = SEGMENT_ICONS[key]

                is_selected = i == st.session_state.selected_segment_idx
                highlight_style = "**" if is_selected else ""
                label = f"{highlight_style}{emoji} {seg['title']} ({format_time(seg['start'])} → {format_time(seg['end'])}){highlight_style}"

                if st.button(label, key=f"clip_{i}"):
                    st.session_state.selected_segment_idx = i
                    st.rerun()

        if len(segments) > 5:
            clip_container.markdown(
                f"""
                <style>
                    .stContainer {{
                        max-height: 300px;
                        overflow-y: auto;
                    }}
                </style>
                """, unsafe_allow_html=True
            )

    # Skipped Chapters
    with tab_skipped:
        skipped_container = st.container()
        with skipped_container:
            for i, seg in enumerate(segments):
                if seg['type'] != 'chapter' or not seg.get('skip', False):
                    continue
                key = next((k for k in SEGMENT_ICONS if k in seg.get('title', '').lower()), "skip")
                emoji, _ = SEGMENT_ICONS[key]
                start_str = format_time(seg['start'])
                end_str = f" → {format_time(seg['end'])}" if seg.get('end') else ""

                is_selected = i == st.session_state.selected_segment_idx
                highlight_style = "**" if is_selected else ""
                label = f"{highlight_style}{emoji} {seg['title']} ({start_str}{end_str}){highlight_style}"

                if st.button(label, key=f"skipped_{i}"):
                    st.session_state.selected_segment_idx = i
                    st.rerun()

        if len(segments) > 5:
            skipped_container.markdown(
                f"""
                <style>
                    .stContainer {{
                        max-height: 300px;
                        overflow-y: auto;
                    }}
                </style>
                """, unsafe_allow_html=True
            )

st.markdown("## 🛠️ Segment Editor")

tab_add_chapter, tab_update_chapter, tab_add_clip, tab_raw_text_editor= st.tabs([
    "➕ Add Chapter",
    "✏️ Update Chapter",
    "🎞️ Add Clip",
    "📄 Raw Text Editor"
])

# --- Add Chapter Tab ---
with tab_add_chapter:
    last_chapter = next((seg for seg in reversed(segments) if seg["type"] == "chapter"), None)
    default_start = last_chapter["end"] if last_chapter else 0
    default_end = default_start + 10
    available_times = [format_time(s) for s in range(int(default_start + 1), 644)] # this is hardcoded duration for the video
    default_end_label = format_time(default_end)
    if default_end_label not in available_times:
        default_end_label = available_times[0]

    with st.expander("➕ Add Chapter Form", expanded=True):
        with st.form("add_chapter_form"):
            st.caption(f"Start Time: {format_time(default_start)}")
            end_label = st.select_slider("Select Chapter End Time", options=available_times, value=default_end_label)
            end_time = int(end_label.split(":")[0]) * 60 + int(end_label.split(":")[1])

            title = st.text_input("Chapter Title")
            skip = st.checkbox("Mark as Skipped", value=False)

            submit = st.form_submit_button("💾 Save Chapter")

            if submit:
                new_chapter = {
                    "type": "chapter",
                    "start": default_start,
                    "end": end_time,
                    "title": title,
                    "skip": skip
                }
                segments.append(new_chapter)
                save_segments(segments)
                st.success("✅ New chapter added!")
                st.rerun()

# --- Update Chapter Tab ---
with tab_update_chapter:
    last_chapter = next((seg for seg in reversed(segments) if seg["type"] == "chapter"), None)
    if not last_chapter:
        st.info("No chapters to update.")
    else:
        default_start = last_chapter["start"]
        default_end = last_chapter["end"]
        default_title = last_chapter.get("title", "")
        default_skip = last_chapter.get("skip", False)

        available_times = [format_time(s) for s in range(int(default_start + 1), 644)] # this is hardcoded duration for the video
        default_end_label = format_time(default_end)
        if default_end_label not in available_times:
            default_end_label = available_times[0]

        with st.expander("✏️ Update Last Chapter", expanded=True):
            with st.form("update_chapter_form"):
                st.caption(f"Start Time: {format_time(default_start)}")
                end_label = st.select_slider("Select Chapter End Time", options=available_times, value=default_end_label)
                end_time = int(end_label.split(":")[0]) * 60 + int(end_label.split(":")[1])

                title = st.text_input("Chapter Title", value=default_title)
                skip = st.checkbox("Mark as Skipped", value=default_skip)

                submit = st.form_submit_button("💾 Update Chapter")

                if submit:
                    updated_chapter = {
                        "type": "chapter",
                        "start": default_start,
                        "end": end_time,
                        "title": title,
                        "skip": skip
                    }

                    idx = segments.index(last_chapter)
                    segments[idx] = updated_chapter
                    save_segments(segments)
                    st.success("✅ Chapter updated!")
                    st.rerun()

            if st.button("🚫 Delete Last Chapter"):
                segments.remove(last_chapter)
                save_segments(segments)
                st.success("❌ Chapter deleted!")
                st.rerun()

# --- Add Clip Tab ---
with tab_add_clip:
    with st.expander("🎞️ Add New Clip", expanded=True):
        with st.form("add_clip_form"):
            start_time = st.number_input("Start Time (s)", min_value=0.0, step=0.1)
            end_time = st.number_input("End Time (s)", min_value=0.1, step=0.1)
            label = st.text_input("Label (e.g., 'guard pass')")
            submitted = st.form_submit_button("Save Clip")

            if submitted and end_time > start_time:
                segments.append({
                    "type": "clip",
                    "start": start_time,
                    "end": end_time,
                    "title": label
                })
                save_segments(segments)
                st.success("✅ Clip saved!")
                st.rerun()

# --- Utility Functions ---
def format_time_to_seconds(time_str):
    """Convert a MM:SS time format string to total seconds."""
    try:
        minutes, seconds = map(int, time_str.split(":"))
        return minutes * 60 + seconds
    except ValueError:
        return None

def parse_raw_text_to_segments(raw_text):
    """Parse raw text into segments as a list of dictionaries."""
    lines = raw_text.splitlines()
    new_segments = []
    section = None

    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
        
        # Check section (Chapters, Clips, Skipped)
        if line.startswith("# "):
            section = line.strip().lower()
            continue
        
        # Attempt to split line into time range and title
        try:
            time_range, title = line.split("|", 1)
        except ValueError:
            st.warning(f"Skipping invalid line (missing '|'): {line}")
            continue
        
        # Split the time range into start and end times
        try:
            start_time, end_time = time_range.split("-")
            start_time = start_time.strip()
            end_time = end_time.strip()

            start_total_seconds = format_time_to_seconds(start_time)
            end_total_seconds = format_time_to_seconds(end_time)

            # Validate time format
            if start_total_seconds is None or end_total_seconds is None:
                st.error(f"Invalid time format in line: {line}")
                continue

            # Check if start is before end
            if start_total_seconds >= end_total_seconds:
                st.error(f"Invalid time range: {start_time} - {end_time}")
                continue
        except ValueError:
            st.error(f"Invalid time format in line: {line}")
            continue

        # Set skip flag to True if this is in the Skipped section
        skip = section == "skipped"

        # Check if it's a clip or chapter based on the section
        seg_type = "clip" if section == "clips" else "chapter"

        # Append new segment
        new_segments.append({
            "start": start_total_seconds,
            "end": end_total_seconds,
            "title": title.strip(),
            "type": seg_type,
            "skip": skip
        })
    
    return new_segments

def convert_segments_to_raw_text(segments):
    """Convert segments (list of dicts) to raw text format."""
    chapter_lines = []
    clip_lines = []
    skipped_lines = []

    for seg in segments:
        start = seg.get("start")
        end = seg.get("end")
        seg_type = seg.get("type", "skipped")
        title = seg.get("title", "")
        skip = seg.get("skip", False)

        start_str = f"{int(start // 60):02}:{int(start % 60):02}"
        end_str = f"{int(end // 60):02}:{int(end % 60):02}"
        line = f"{start_str} - {end_str} | {title.strip()}"

        if seg_type == "chapter" and not skip:
            chapter_lines.append(line)
        elif seg_type == "clip":
            clip_lines.append(line)
        elif skip:
            skipped_lines.append(line)

    if not skipped_lines:
        skipped_lines.append("# (none)")

    raw_text = "# Chapters\n" + "\n".join(chapter_lines)
    raw_text += "\n\n# Clips\n" + "\n".join(clip_lines)
    raw_text += "\n\n# Skipped\n" + "\n".join(skipped_lines)
    
    return raw_text

# --- Streamlit Interface ---
# with st.expander("Edit Segments in Raw Text Format"):
with tab_raw_text_editor:
    with st.expander("📄 Edit Segments in Raw Text Format", expanded=True):
    # st.markdown("### 📄 Edit Segments in Raw Text Format")

        # Load existing segments (for editing)
        try:
            with open("segments.json", "r") as f:
                segments = json.load(f)
        except FileNotFoundError:
            segments = []

        # Convert segments to raw text format
        raw_text = convert_segments_to_raw_text(segments)
        
        updated_raw_text = st.text_area("Edit Raw Text Format", value=raw_text, height=400)

    # Save Changes Button
    if st.button("💾 Save Changes"):
        try:
            # Convert updated raw text back to segments
            new_segments = parse_raw_text_to_segments(updated_raw_text)

            # Save to segments.json
            with open("segments.json", "w") as f:
                json.dump(new_segments, f, indent=4)

            st.success("✅ Raw Text saved successfully!")
        except Exception as e:
            st.error(f"Error: {e}")

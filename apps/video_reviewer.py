# apps/video_reviewer.py
import streamlit as st # type: ignore
import json
import math
import os
import re
import streamlit.components.v1 as components # type: ignore
from hydralit import HydraHeadApp # type: ignore
from utils import load_videos, load_clips, save_clips, convert_clips_to_raw_text, format_time, embed_youtube_player
from utils import parse_clip_line # TODO: check if 'start' and 'end' are in video's duration


class VRApp(HydraHeadApp):

    def run(self):

        videos = load_videos()
        video_options = {f"{v['title']} ({v['video_id']})": v["video_id"] for v in videos}
        col11, col12 = st.columns([11, 1])
        with col11:
            selected_label = st.selectbox("Choose a video", list(video_options.keys()))
        with col12:
            layout_ratio = st.selectbox("", ["3:1", "2:1", "1:1", "1:2", "1:3"])
        ratios = {"3:1": [3,1], "2:1": [2,1], "1:1": [1,1], "1:2": [1,2], "1:3": [1,3]}
        col1, col2 = st.columns(ratios[layout_ratio])

        if selected_label:
            selected_video_id = video_options[selected_label]
            st.session_state.selected_video = selected_video_id #TODO: test

        if selected_video_id:
            selected_video = next((v for v in videos if v["video_id"] == selected_video_id), None)
            segments = load_clips(selected_video_id)

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
            else:
                start = 0
                end = None
            speed = st.session_state.playback_speed

            with st.container():
                # Embed video player
                embed_youtube_player(selected_video_id, start, end, speed)

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

        # --- Clipper (Col2) ---
        with col2:
            with st.form("clipper"):

                # Load existing segments (for editing)
                segments = load_clips(selected_video_id)

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
                        save_clips(selected_video_id, new_clips)
                        st.rerun()
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

                        is_selected = i == st.session_state.selected_segment_idx
                        highlight_style = "**" if is_selected else ""
                        label = f"{highlight_style}{seg['title']} ({format_time(seg['start'])} → {format_time(seg['end'])}){highlight_style}"

                        if cols[col_idx].button(label, key=f"clip_{i}"):
                            st.session_state.selected_segment_idx = i
                            st.rerun()
            if not clip_buttons:
                st.warning(f"No clips found for the video: {selected_video_id}!")


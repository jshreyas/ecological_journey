# apps/partner.py
import streamlit as st # type: ignore
import pandas as pd # type: ignore
from utils import load_videos, find_clips_by_partner, format_time, get_all_partners, embed_youtube_player
from hydralit import HydraHeadApp # type: ignore
import math

class PartnerApp(HydraHeadApp):

    def run(self):

        st.title("🤼 Meet our Training Partners!")

        selected_partner = st.selectbox("Choose a partner", get_all_partners())

        clips = find_clips_by_partner(selected_partner)

        # Default state
        if "selected_segment_idx" not in st.session_state:
            st.session_state.selected_segment_idx = 0
        if "playback_speed" not in st.session_state:
            st.session_state.playback_speed = 1.0

        # --- Main Video Player (Col1) ---
        if clips:
            seg = clips[st.session_state.selected_segment_idx]
            start = seg.get("start", 0)
            end = seg.get("end", 0)
        else:
            start = 0
            end = None
        speed = st.session_state.playback_speed

        with st.container():
            # Embed video player
            embed_youtube_player(seg.get("video_id"), start, end, speed)

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


        clip_container = st.container()
        with clip_container:

            # Customize number of columns based on screen size or fixed value
            NUM_COLUMNS = 3

            clip_buttons = [seg for seg in clips if seg["type"] == "clip"]
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

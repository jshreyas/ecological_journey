# apps/partner.py
import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
from utils import find_clips_by_partner, format_time, get_all_partners, embed_youtube_player
from hydralit import HydraHeadApp  # type: ignore
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

        if clips:
            seg = clips[st.session_state.selected_segment_idx]
            start = seg.get("start", 0)
            end = seg.get("end", 0)
        else:
            start = 0
            end = None

        speed = st.session_state.playback_speed

        with st.container():
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

        if new_speed != st.session_state.playback_speed:
            st.session_state.playback_speed = new_speed
            st.rerun()

        col1, col2 = st.columns([3, 1])
        segments = clips

        # --- Label Analysis ---
        labels_set = set()
        has_no_label = False
        for seg in segments:
            if seg.get("type") == "clip":
                labels = seg.get("labels") or []
                if labels:
                    labels_set.update(labels)
                else:
                    has_no_label = True

        all_labels = sorted(labels_set)
        if has_no_label:
            all_labels.append("No Label")  # Use this as the label key

        # Initialize session state for filters
        if "label_filter" not in st.session_state:
            st.session_state.label_filter = {label: True for label in all_labels}
        for label in all_labels:
            if label not in st.session_state.label_filter:
                st.session_state.label_filter[label] = True

        with col2:
            st.markdown("### Filter by Labels")

            for label in all_labels:
                st.session_state.label_filter[label] = st.checkbox(
                    label,
                    value=st.session_state.label_filter.get(label, True),
                    key=f"filter_{label}"
                )

        selected_labels = [label for label, checked in st.session_state.label_filter.items() if checked]

        def is_clip_visible(clip):
            labels = clip.get("labels") or []
            is_empty = not labels
            if is_empty and "No Label" in selected_labels:
                return True
            return any(label in selected_labels for label in labels)

        visible_clips = [seg for seg in segments if seg["type"] == "clip" and is_clip_visible(seg)]

        with col1:
            st.markdown("### Clips")
            NUM_COLUMNS = 3
            num_rows = math.ceil(len(visible_clips) / NUM_COLUMNS)

            for row in range(num_rows):
                cols = st.columns(NUM_COLUMNS)
                for col_idx in range(NUM_COLUMNS):
                    i = row * NUM_COLUMNS + col_idx
                    if i < len(visible_clips):
                        seg = visible_clips[i]
                        is_selected = i == st.session_state.get("selected_segment_idx", -1)
                        highlight_style = "**" if is_selected else ""
                        label = f"{highlight_style}{seg['title']} ({format_time(seg['start'])} → {format_time(seg['end'])}){highlight_style}"
                        if cols[col_idx].button(label, key=f"clip_{i}"):
                            st.session_state.selected_segment_idx = i
                            st.rerun()

            if not visible_clips:
                st.warning("No clips found for the selected labels!")

import streamlit as st
import json
import math
import datetime

st.title("📂 Grappling Video Archive")

# VIDEOS_JSON_FILE = "videos.json"
VIDEOS_JSON_FILE = "fetch_videos.json"

with open(VIDEOS_JSON_FILE) as f:
    videos = json.load(f)

# Sidebar filters
st.sidebar.header("Filter Videos")
partners = sorted(list(set(v["partner"] for v in videos)))
types = sorted(list(set(v["type"] for v in videos)))
positions = sorted(list({p for v in videos for p in v["positions"]}))

date_range = st.sidebar.date_input("Filter by Date Range", [])
selected_partner = st.sidebar.selectbox("Training Partner", ["All"] + partners)
selected_type = st.sidebar.selectbox("Video Type", ["All"] + types)
selected_positions = st.sidebar.multiselect("Positions", positions)

# Filter logic
def filter_video(video):
    if selected_partner != "All" and video["partner"] != selected_partner:
        return False
    if selected_type != "All" and video["type"] != selected_type:
        return False
    if selected_positions and not any(pos in video["positions"] for pos in selected_positions):
        return False
    if date_range:
        vdate = datetime.datetime.strptime(video["date"], "%Y-%m-%dT%H:%M:%SZ").date()
        if vdate < date_range[0] or vdate > date_range[-1]:
            return False
    return True

filtered = list(filter(filter_video, videos))

# Pagination
items_per_page = 10
page = st.sidebar.number_input("Page", min_value=1, max_value=max(1, math.ceil(len(filtered) / items_per_page)), step=1)
start = (page - 1) * items_per_page
end = start + items_per_page

if not filtered:
    st.warning("No videos found.")
else:
    for v in filtered[start:end]:
        st.subheader(v["title"])
        st.video(v["youtube_url"])
        st.markdown(f"**Partner:** {v['partner']} | **Type:** {v['type']} | **Date:** {v['date']}")
        st.markdown(f"**Positions:** {', '.join(v['positions'])}")
        st.markdown(f"_Notes:_ {v['notes']}")
        st.markdown("---")

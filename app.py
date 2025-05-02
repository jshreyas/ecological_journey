import streamlit as st
import json
import datetime

# VIDEOS_JSON_FILE = "videos.json"
VIDEOS_JSON_FILE = "fetch_videos.json"

# Load video metadata
with open(VIDEOS_JSON_FILE) as f:
    videos = json.load(f)

# Convert date strings to datetime.date objects
for v in videos:
    v["date"] = datetime.datetime.strptime(v["date"], "%Y-%m-%dT%H:%M:%SZ").date()

# Sidebar filters
st.sidebar.title("Filter Videos")

partners = sorted(list(set(v["partner"] for v in videos)))
types = sorted(list(set(v["type"] for v in videos)))
positions = sorted(list({p for v in videos for p in v["positions"]}))
dates = sorted(list(set(v["date"] for v in videos)))

selected_partner = st.sidebar.selectbox("Training Partner", ["All"] + partners)
selected_type = st.sidebar.selectbox("Video Type", ["All"] + types)
selected_positions = st.sidebar.multiselect("Positions", positions)
selected_date = st.sidebar.date_input("Filter by Date", value=None)

# Filter logic
def filter_video(video):
    if selected_partner != "All" and video["partner"] != selected_partner:
        return False
    if selected_type != "All" and video["type"] != selected_type:
        return False
    if selected_positions and not any(pos in video["positions"] for pos in selected_positions):
        return False
    if selected_date and video["date"] != selected_date:
        return False
    return True

filtered_videos = list(filter(filter_video, videos))

# Main area display
st.title("🎥 Grappling Video Archive")

if not filtered_videos:
    st.write("No videos match the selected filters.")
else:
    for v in filtered_videos:
        st.subheader(v["title"])
        st.video(v["youtube_url"])
        st.markdown(f"**Partner:** {v['partner']} | **Type:** {v['type']} | **Date:** {v['date'].isoformat()}")
        st.markdown(f"**Positions:** {', '.join(v['positions'])}")
        st.markdown(f"_Notes:_ {v['notes']}")
        st.markdown("---")
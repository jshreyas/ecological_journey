import streamlit as st
import json
from collections import defaultdict

st.title("🧑‍🤝‍🧑 Partner Profiles")
# VIDEOS_JSON_FILE = "videos.json"
VIDEOS_JSON_FILE = "fetch_videos.json"

with open(VIDEOS_JSON_FILE) as f:
    videos = json.load(f)

partners = sorted(set(v["partner"] for v in videos))
selected = st.selectbox("Select Partner", partners)

partner_videos = [v for v in videos if v["partner"] == selected]

st.markdown(f"### {selected} – {len(partner_videos)} Sessions")

pos_counter = defaultdict(int)
types = defaultdict(int)

for v in partner_videos:
    for pos in v["positions"]:
        pos_counter[pos] += 1
    types[v["type"]] += 1

st.markdown("#### Position Frequency")
st.write(dict(pos_counter))

st.markdown("#### Video Types")
st.write(dict(types))

for v in partner_videos:
    st.subheader(v["title"])
    st.video(v["youtube_url"])
    st.markdown(f"**Type:** {v['type']} | **Date:** {v['date']}")
    st.markdown(f"**Positions:** {', '.join(v['positions'])}")
    st.markdown(f"_Notes:_ {v['notes']}")
    st.markdown("---")

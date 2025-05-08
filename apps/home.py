# apps/home.py
import streamlit as st # type: ignore
import pandas as pd # type: ignore
import json
from hydralit import HydraHeadApp # type: ignore

VIDEOS_JSON_FILE = ["fetch_videos.json", "home_training.json"]

def load_videos():
    loaded_videos = []
    for path in VIDEOS_JSON_FILE:
        with open(path) as f:
            loaded_videos = loaded_videos + json.load(f)
    return loaded_videos


class HomeApp(HydraHeadApp):

    def run(self):

        st.title("🤼 Grappling Portfolio Dashboard")
        videos = load_videos()
        df = pd.DataFrame(videos)
        df["date"] = pd.to_datetime(df["date"])

        col1, col2, col3 = st.columns(3)
        col1.metric("📹 Total Videos", len(df))
        unique_partners = set(p for partners in df['partners'] for p in partners)
        col2.metric("🧑‍🤝‍🧑 Training Partners", len(unique_partners))
        col3.metric("📍 Unique Positions", len(set(p for v in videos for p in v['positions'])))

        st.subheader("Activity Over Time")
        daily_counts = df.groupby(df["date"].dt.date).size()
        st.bar_chart(daily_counts)

        st.subheader("Latest Uploads")
        latest_videos = df.sort_values("date", ascending=False).head(5)
        for _, v in latest_videos.iterrows():
            st.markdown(f"**{v['title']}** ({v['date'].date()})")
            st.video(v['youtube_url'])
            st.markdown(f"Partners: {', '.join(v['partners'])} | Type: {v['type']} | Positions: {', '.join(v['positions'])}")
            st.markdown(f"_Notes:_ {v['notes']}")
            st.markdown("---")

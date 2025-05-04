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
partners = sorted(list({p for v in videos for p in v["partners"]}))
types = sorted(list(set(v["type"] for v in videos)))
positions = sorted(list({p for v in videos for p in v["positions"]}))

date_range = st.sidebar.date_input("Filter by Date Range", [])
selected_partner = st.sidebar.selectbox("Training Partner", ["All"] + partners) #TODO: make this multi select
selected_type = st.sidebar.selectbox("Video Type", ["All"] + types)
selected_positions = st.sidebar.multiselect("Positions", positions)

# Filter logic
def filter_video(video):
    if selected_partner != "All" and selected_partner not in video["partners"]:
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

all_partners = ["Shreyas", "Eric", "Keshav"]

if not filtered:
    st.warning("No videos found.")
else:
    for v in filtered[start:end]:
        st.subheader(v["title"])
        st.video(v["youtube_url"])
        # st.markdown(f"**Positions:** {', '.join(v['positions'])}")
        with st.form(key=v["video_id"]):
            partners = st.multiselect("Partners", options=all_partners, default=v.get("partners", []))
            # type_ = st.selectbox("Type", options=video_types, index=video_types.index(v.get("type", "Game")) if v.get("type", "Game") in video_types else 0)
            # positions = st.multiselect("Positions", options=all_positions, default=v.get("positions", []))
            notes = st.text_area("Notes", value=v.get("notes", ""))
            timestamps = st.text_area("Timestamps & Commentary", value=v.get("timestamps", ""))

            submitted = st.form_submit_button("Save Metadata")
            if submitted:
                # Update dict
                v["partners"] = partners
                # v["type"] = type_
                # v["positions"] = positions
                v["notes"] = notes
                v["timestamps"] = timestamps

                # Save to file
                with open(VIDEOS_JSON_FILE, "w") as f:
                    json.dump(videos, f, indent=2)

                st.success("Metadata saved!")

        st.markdown("---")

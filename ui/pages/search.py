from typing import Any, Dict, Optional

from nicegui import ui

from ui.utils.utils import format_time
from ui.utils.utils_api import load_clips, load_videos


def build_thumbnail_html(thumbnail_url: str, href: str) -> str:
    return f"""
    <a href="{href}">
        <img
            src="{thumbnail_url}"
            style="
                width:96px;
                height:54px;
                object-fit:cover;
                border-radius:6px;
            "
        />
    </a>
    """


class State:
    """Centralized state management for search page"""

    def __init__(self):
        self._load_videos: Optional[Dict[str, Any]] = None
        self._load_clips: Optional[Dict[str, Any]] = None

    def load_videos(self) -> Optional[Dict[str, Any]]:
        """Get videos data, loading from API if not cached"""
        if self._load_videos is None:
            self._load_videos = load_videos()
        return self._load_videos

    def load_clips(self):
        if self._load_clips is None:
            self._load_clips = load_clips()
        return self._load_clips


class VideosTab:

    COLUMN_DEFS = [
        {
            "headerName": "",
            "field": "thumbnail",
            "width": 100,
            "sortable": False,
            "filter": False,
        },
        {
            "headerName": "Playlist",
            "field": "playlist",
            "filter": "agTextColumnFilter",
            "width": 120,
        },
        {
            "headerName": "Date",
            "field": "date",
            "filter": "agDateColumnFilter",
            "sort": "desc",
            "width": 100,
        },
        {
            "headerName": "Runtime",
            "field": "duration",
            "width": 100,
        },
        {
            "headerName": "Anchors",
            "field": "anchor_count",
            "width": 60,
            "filter": "agNumberColumnFilter",
        },
        {
            "headerName": "Clips",
            "field": "clip_count",
            "width": 60,
            "filter": "agNumberColumnFilter",
        },
        {
            "headerName": "Notes",
            "field": "notes",
            "filter": "agTextColumnFilter",
            # "flex": 3,
            # "wrapText": True,
            # "autoHeight": True,
        },
    ]

    def __init__(self, state: State):
        self.rows = []
        self.state = state

    def create_tab(self, container):
        self.container = container
        videos = self.state.load_videos()
        for video in videos:
            thumbnail = video.get("thumbnail_url") or f"https://img.youtube.com/vi/{video['video_id']}/0.jpg"
            thumbnail = f'<a href="film/{video["video_id"]}"><img src="{thumbnail}" alt="Thumbnail description" style="width:96px;height:54px;object-fit:cover;border-radius:6px;" /></a>'
            self.rows.append(
                {
                    "video_id": video["video_id"],
                    "thumbnail": thumbnail,
                    "title": video["title"],
                    "duration": format_time(int(video.get("duration_seconds", 0))),
                    "notes": video.get("notes", ""),
                    "anchor_count": len(video.get("anchors", [])),
                    "clip_count": len(video.get("clips", [])),
                    "playlist": video.get("playlist_name", ""),
                    "date": video["date"][:10],
                }
            )
        self.rows.sort(
            key=lambda r: r["date"],
            reverse=True,
        )
        with self.container:
            ui.aggrid(
                {
                    "columnDefs": self.COLUMN_DEFS,
                    "rowData": self.rows,
                    "pagination": True,
                    "paginationPageSize": 50,
                    "animateRows": True,
                    "rowHeight": 70,
                    "defaultColDef": {
                        "sortable": True,
                        "filter": True,
                        "resizable": True,
                        "floatingFilter": True,
                    },
                },
                html_columns=[0],
                modules="community",
            ).classes("w-full h-[600px]")


class ClipsTab:

    COLUMN_DEFS = [
        # TODO: add clip selection and bulk actions for cliplists
        # {
        #     "checkboxSelection": True,
        #     "headerCheckboxSelection": True,
        #     "width": 60,
        #     "pinned": "left",
        # },
        {
            "headerName": "",
            "field": "thumbnail",
            "width": 100,
            "sortable": False,
            "filter": False,
        },
        {
            "headerName": "Playlist",
            "field": "playlist",
            "filter": "agTextColumnFilter",
            "width": 120,
        },
        {
            "headerName": "Date",
            "field": "date",
            "filter": "agDateColumnFilter",
            "sort": "desc",
            "width": 100,
        },
        {
            "headerName": "Video",
            "field": "video_title",
            "filter": "agTextColumnFilter",
            "width": 100,
        },
        {
            "headerName": "Duration",
            "field": "duration",
            "width": 80,
        },
        {
            "headerName": "Notes",
            "field": "notes",
            "filter": "agTextColumnFilter",
        },
    ]

    def __init__(self, state: State):
        self.rows = []
        self.state = state

    def create_tab(self, container):
        self.container = container
        clips = self.state.load_clips()
        for clip in clips:
            video_id = clip["video_id"]
            clip_id = clip["clip_id"]
            thumbnail = clip.get("thumbnail_url") or f"https://img.youtube.com/vi/{video_id}/0.jpg"
            thumbnail = build_thumbnail_html(
                thumbnail,
                f"film/{video_id}?clip={clip_id}",
            )
            self.rows.append(
                {
                    "clip_id": clip_id,
                    "video_id": video_id,
                    "thumbnail": thumbnail,
                    "title": clip.get("title", ""),
                    "duration": clip.get("duration_human", 0),
                    "notes": clip.get("description", ""),
                    "video_title": clip.get("video_id", ""),
                    "playlist": clip.get("playlist_name", ""),
                    "date": clip["date"][:10],
                }
            )
        self.rows.sort(
            key=lambda r: r["date"],
            reverse=True,
        )
        with self.container:
            ui.aggrid(
                {
                    "columnDefs": self.COLUMN_DEFS,
                    "rowData": self.rows,
                    "pagination": True,
                    "paginationPageSize": 50,
                    "rowHeight": 70,
                    "animateRows": True,
                    # "rowSelection": "multiple",
                    "defaultColDef": {
                        "sortable": True,
                        "filter": True,
                        "floatingFilter": True,
                        "resizable": True,
                    },
                },
                html_columns=[0],
                modules="community",
            ).classes("w-full h-[600px]")


class CliplistsTab:

    def __init__(self, state: State):
        self.rows = []
        self.state = state

    def create_tab(self, container):
        self.container = container
        with self.container:
            ui.label("Cliplists coming soon!").classes("text-center text-gray-500 mt-20")


def search_page():
    state = State()
    videos_tab = VideosTab(state)
    clips_tab = ClipsTab(state)
    cliplists_tab = CliplistsTab(state)

    with ui.tabs().classes("w-full") as tabs:
        tab_films = ui.tab("🎵 Films").classes("w-full border border-gray-300")
        tab_clips = ui.tab("🎵 Clips").classes("w-full border border-gray-300")
        tab_cliplists = ui.tab("🎵 Cliplists").classes("w-full border border-gray-300")
    with ui.tab_panels(tabs, value=tab_clips).classes("w-full h-full"):
        with ui.tab_panel(tab_films) as video_container:
            videos_tab.create_tab(video_container)
        with ui.tab_panel(tab_clips) as clips_container:
            clips_tab.create_tab(clips_container)
        with ui.tab_panel(tab_cliplists) as cliplists_container:
            cliplists_tab.create_tab(cliplists_container)

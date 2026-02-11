"""
FilmboardTab - Component for displaying videos from the same day
Handles the filmboard functionality for showing related videos
"""

from typing import Callable

from nicegui import ui

from ui.utils.utils import navigate_to_film
from ui.utils.utils_api import load_videos

from .video_state import VideoState


class FilmboardTab:
    """Component for displaying videos from the same day"""

    def __init__(self, video_state: VideoState, on_video_select: Callable = None):
        self.video_state = video_state
        self.on_video_select = on_video_select
        self.container = None

    def create_tab(self, container):
        """Create the filmboard tab UI"""
        self.container = container
        self.refresh()

    def refresh(self):
        """Refresh the filmboard tab with current video data"""
        if not self.container:
            return

        self.container.clear()
        with self.container:
            self._create_filmboard_ui()

    def _create_filmboard_ui(self):
        """Create the filmboard UI"""
        video = self.video_state.get_video()
        if not video:
            ui.label("No video data available")
            return

        current_video_date = video.get("date", "").split("T")[0]
        if not current_video_date:
            ui.label("No date information available")
            return

        # Get videos from the same day
        all_videos = load_videos()
        same_day_videos = [
            v
            for v in all_videos
            if v["video_id"] != self.video_state.video_id and v.get("date", "").split("T")[0] == current_video_date
        ]

        if not same_day_videos:
            ui.label("📭 No other films found from the same day.").classes("text-sm text-gray-500")
            return

        # Display videos from the same day using the original layout
        for v in same_day_videos:
            partners = v.get("partners", [])
            labels = v.get("labels", [])
            partners_html = ", ".join(p for p in partners) if partners else "No partners"
            labels_html = ", ".join(label for label in labels) if labels else "No labels"

            card_classes = (
                "cursor-pointer flex flex-row flex-col p-2 hover:shadow-xl "
                "transition-shadow duration-200 border-gray-600"
            )
            with (
                ui.card().classes(card_classes).on("click", lambda e, vid=v["video_id"]: self._handle_video_click(vid))
            ):
                with ui.row().classes("w-full gap-2 justify-between"):
                    ui.label(v["title"]).tooltip(v["title"]).classes("truncate font-bold text-sm sm:text-base")
                    ui.label(f"⏱ {v['duration_human']}").classes("text-xs")
                ui.label(f"🎭 {partners_html}").classes("text-xs")
                ui.label(f"🏷️ {labels_html}").classes("text-xs")
                with ui.row().classes("w-full gap-2 justify-between"):
                    ui.label(f"📂 {v['playlist_name']}").classes("text-xs text-primary")
                    ui.label(f"🎬 {len(v.get('clips', 0))}").classes("text-xs")

    def _handle_video_click(self, video_id):
        """Handle video click"""
        if self.on_video_select:
            self.on_video_select(video_id)
        else:
            navigate_to_film(video_id)

    def get_same_day_videos_count(self):
        """Get count of videos from the same day"""
        video = self.video_state.get_video()
        if not video:
            return 0

        current_video_date = video.get("date", "").split("T")[0]
        if not current_video_date:
            return 0

        all_videos = load_videos()
        same_day_videos = [
            v
            for v in all_videos
            if v["video_id"] != self.video_state.video_id and v.get("date", "").split("T")[0] == current_video_date
        ]

        return len(same_day_videos)

    def get_current_video_date(self):
        """Get the current video date"""
        video = self.video_state.get_video()
        if not video:
            return ""

        return video.get("date", "").split("T")[0]

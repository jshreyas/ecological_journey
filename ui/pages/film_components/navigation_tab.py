"""
NavigationTab - Component for navigating between videos by date
Handles the navigation arrows functionality
"""

from datetime import datetime
from typing import Callable, Optional

from nicegui import ui
from utils.utils import navigate_to_film
from utils.utils_api import load_videos

from .video_state import VideoState


class NavigationTab:
    """Component for navigating between videos by date"""

    def __init__(self, video_state: VideoState, on_video_select: Callable = None):
        self.video_state = video_state
        self.on_video_select = on_video_select
        self.container = None
        self.prev_video = None
        self.next_video = None

    def create_tab(self, container):
        """Create the navigation tab UI"""
        self.container = container
        self.refresh()

    def refresh(self):
        """Refresh the navigation with current video data"""
        if not self.container:
            return

        self.container.clear()
        with self.container:
            self._find_adjacent_videos()
            self._create_navigation_ui()

    def _find_adjacent_videos(self):
        """Find the last video from the previous day and the first video from the next day."""
        video = self.video_state.get_video()
        if not video:
            self.prev_video = None
            self.next_video = None
            return
        current_video_date = video.get("date", "").split("T")[0]

        if not current_video_date:
            self.prev_video = None
            self.next_video = None
            return

        all_videos = load_videos()

        # Sort videos by date
        sorted_videos = sorted(all_videos, key=lambda v: v.get("date", ""))
        self.prev_video = None
        self.next_video = None

        for i, v in enumerate(sorted_videos):
            if v["video_id"] == self.video_state.video_id:
                # Find the last video from the previous day
                for j in range(i - 1, -1, -1):
                    if sorted_videos[j]["date"].split("T")[0] < current_video_date:
                        self.prev_video = sorted_videos[j]
                        break

                # Find the first video from the next day
                for j in range(i + 1, len(sorted_videos)):
                    if sorted_videos[j]["date"].split("T")[0] > current_video_date:
                        self.next_video = sorted_videos[j]
                        break
                break

    def _create_navigation_ui(self):
        """Create the navigation UI with arrows"""
        video = self.video_state.get_video()

        # Navigation Arrows
        with ui.row().classes("w-full justify-between items-center"):
            # Use a 3-column grid for consistent centering
            with ui.grid(columns=3).classes("w-full items-center"):
                # Previous
                if self.prev_video:
                    with (
                        ui.row()
                        .classes("items-center cursor-pointer justify-start")
                        .on(
                            "click",
                            lambda e: self._handle_video_click(self.prev_video["video_id"]),
                        )
                    ):
                        ui.icon("arrow_back").classes("text-primary text-bold")
                        prev_date = datetime.strptime(self.prev_video["date"], "%Y-%m-%dT%H:%M:%SZ").strftime(
                            "%B %d, %Y"
                        )
                        ui.label(f"Previous Day: {prev_date}").classes("text-sm text-primary text-bold truncate")
                else:
                    ui.label().classes("")  # Empty cell

                # Center label
                with ui.row().classes("justify-center"):
                    ui.label(f'🔍 🎬 {video.get("title", "Untitled Video")}').classes("text-2xl font-bold")

                # Next
                if self.next_video:
                    with (
                        ui.row()
                        .classes("items-center cursor-pointer justify-end")
                        .on(
                            "click",
                            lambda e: self._handle_video_click(self.next_video["video_id"]),
                        )
                    ):
                        next_date = datetime.strptime(self.next_video["date"], "%Y-%m-%dT%H:%M:%SZ").strftime(
                            "%B %d, %Y"
                        )
                        ui.label(f"Next Day: {next_date}").classes("text-sm text-primary text-bold truncate")
                        ui.icon("arrow_forward").classes("text-primary text-bold")
                else:
                    ui.label().classes("")  # Empty cell

    def _handle_video_click(self, video_id):
        """Handle video navigation click"""
        if self.on_video_select:
            self.on_video_select(video_id)
        else:
            navigate_to_film(video_id)

    def get_adjacent_videos(self) -> tuple[Optional[dict], Optional[dict]]:
        """Get the adjacent videos (previous and next)"""
        return self.prev_video, self.next_video

    def get_current_video_title(self) -> str:
        """Get the current video title"""
        video = self.video_state.get_video()
        return video.get("title", "Untitled Video") if video else "Untitled Video"

from typing import Any, Callable, Dict, List, Optional

from ui.utils.user_context import User
from ui.utils.utils_api import load_videos


class State:
    """Centralized state management for home page and refresh callbacks"""

    def __init__(self, user: User | None = None):
        self.user = user
        self._video_data: Optional[Dict[str, Any]] = None  # TODO: use this in all the tabs
        self._refresh_callbacks: List[Callable] = []

    def refresh(self):
        """Clear cache and notify all registered callbacks"""
        self._video_data = load_videos()
        for callback in self._refresh_callbacks:
            callback()

    def get_date_anchor(self, date_str: str):
        return f"date-{date_str.split('T')[0]}"

    def get_video_anchor(self, video_id: str):
        return f"video-{video_id}"

    def get_videos(self) -> Optional[Dict[str, Any]]:
        """Get videos data, loading from API if not cached"""
        if self._video_data is None:
            self._video_data = load_videos()
        return self._video_data

    def add_refresh_callback(self, callback: Callable):
        """Register a callback to be called when video data is refreshed"""
        if callback not in self._refresh_callbacks:
            self._refresh_callbacks.append(callback)

    def remove_refresh_callback(self, callback: Callable):
        """Remove a registered refresh callback"""
        if callback in self._refresh_callbacks:
            self._refresh_callbacks.remove(callback)

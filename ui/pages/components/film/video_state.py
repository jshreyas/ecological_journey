"""
VideoState class for centralized state management of video data
"""

from typing import Any, Callable, Dict, List, Optional  # All used in type annotations

from utils.utils_api import load_video


class VideoState:
    """Centralized state management for video data and refresh callbacks"""

    def __init__(self, video_id: str):
        self.video_id = video_id
        self._video_data: Optional[Dict[str, Any]] = None
        self._refresh_callbacks: List[Callable] = []
        self.conversation: List[Dict[str, Any]] = []

    def get_video(self) -> Optional[Dict[str, Any]]:
        """Get video data, loading from API if not cached"""
        if self._video_data is None:
            self._video_data = load_video(self.video_id)
        return self._video_data

    def refresh(self):
        """Clear cache and notify all registered callbacks"""
        self._video_data = load_video(self.video_id)
        for callback in self._refresh_callbacks:
            callback()

    def add_refresh_callback(self, callback: Callable):
        """Register a callback to be called when video data is refreshed"""
        if callback not in self._refresh_callbacks:
            self._refresh_callbacks.append(callback)

    def remove_refresh_callback(self, callback: Callable):
        """Remove a registered refresh callback"""
        if callback in self._refresh_callbacks:
            self._refresh_callbacks.remove(callback)

    def clear_cache(self) -> None:
        """Clear cached video data, forcing reload on next get_video()"""
        self._video_data = None

    def get_clips(self) -> list[Dict[str, Any]]:
        """Get clips from current video data"""
        return self.get_video().get("clips", [])

    def get_partners(self) -> list[str]:
        """Get partners from current video data"""
        return self.get_video().get("partners", [])

    def get_labels(self) -> list[str]:
        """Get labels from current video data"""
        return self.get_video().get("labels", [])

    def get_notes(self) -> str:
        """Get notes from current video data"""
        return self.get_video().get("notes", "")

    def is_peertube(self) -> bool:
        """Check if the video source is PeerTube"""
        return "peertube" == self._video_data.get("playlist_source")

    def get_url(self) -> bool:
        """Check if the video source is PeerTube"""
        return self._video_data.get("youtube_url")

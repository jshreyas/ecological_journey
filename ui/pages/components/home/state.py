from typing import Any, Callable, Dict, List, Optional

from ui.data.crud import load_playlists as lp
from ui.utils.user_context import User
from ui.utils.utils_api import create_playlist as cp
from ui.utils.utils_api import create_video as cv
from ui.utils.utils_api import load_playlists_for_user as lp_user
from ui.utils.utils_api import load_videos as lv


class State:
    """Centralized state management for home page and refresh callbacks"""

    def __init__(self, user: User | None = None):
        self.user = user
        self._load_videos: Optional[Dict[str, Any]] = None
        self._refresh_callbacks: List[Callable] = []
        self._load_playlists: Optional[Dict[str, Any]] = None
        self._load_playlists_user: Optional[Dict[str, Any]] = None

    def refresh(self):
        """Clear cache and notify all registered callbacks"""
        self._load_videos = lv()
        self._load_playlists = lp()
        for callback in self._refresh_callbacks:
            callback()

    def get_date_anchor(self, date_str: str):
        return f"date-{date_str.split('T')[0]}"

    def get_video_anchor(self, video_id: str):
        return f"video-{video_id}"

    def create_playlist(self, playlist_name: str, playlist_id: str) -> Optional[Dict[str, Any]]:
        """Create a new playlist and refresh state"""
        created_playlist = cp([], self.user.token if self.user else "", playlist_name, playlist_id)
        if created_playlist:
            self.refresh()
        return created_playlist

    def create_video(self, video_data: Dict[str, Any], playlist_id: str) -> Optional[Dict[str, Any]]:
        """Create a new video and refresh state"""
        created_video = cv(video_data, self.user.token if self.user else "", playlist_id)
        if created_video:
            self.refresh()
        return created_video

    def load_videos(self, playlist_id: str = None) -> Optional[Dict[str, Any]]:
        """Get videos data, loading from API if not cached"""
        if self._load_videos is None:
            if playlist_id:
                self._load_videos = lv(playlist_id)
            else:
                self._load_videos = lv()
        return self._load_videos

    def load_playlists(self) -> Optional[Dict[str, Any]]:
        """Get playlists data, loading from API if not cached"""
        if self._load_playlists is None:
            self._load_playlists = lp()
        return self._load_playlists

    def load_playlists_for_user(self) -> Optional[Dict[str, Any]]:
        """Get playlists for user data, loading from API if not cached"""
        if self._load_playlists_user is None:
            self._load_playlists_user = lp_user(self.user.id) if self.user else []
        return self._load_playlists_user

    def add_refresh_callback(self, callback: Callable):
        """Register a callback to be called when video data is refreshed"""
        if callback not in self._refresh_callbacks:
            self._refresh_callbacks.append(callback)

    def remove_refresh_callback(self, callback: Callable):
        """Remove a registered refresh callback"""
        if callback in self._refresh_callbacks:
            self._refresh_callbacks.remove(callback)

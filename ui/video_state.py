"""
VideoState - Centralized state management for video data
Handles loading, caching, and notifying components of data changes
"""
from typing import Callable, Optional, Dict, Any
from utils.utils_api import load_video


class VideoState:
    """Centralized state management for video data"""
    
    def __init__(self, video_id: str):
        self.video_id = video_id
        self._video_data: Optional[Dict[str, Any]] = None
        self._refresh_callbacks: list[Callable] = []
    
    def get_video(self) -> Dict[str, Any]:
        """Get current video data, loading if necessary"""
        if self._video_data is None:
            self._video_data = load_video(self.video_id)
        return self._video_data
    
    def refresh(self) -> None:
        """Refresh video data and notify all callbacks"""
        self._video_data = load_video(self.video_id)
        for callback in self._refresh_callbacks:
            callback()
    
    def add_refresh_callback(self, callback: Callable) -> None:
        """Register a callback to be called when video data is refreshed"""
        self._refresh_callbacks.append(callback)
    
    def remove_refresh_callback(self, callback: Callable) -> None:
        """Remove a registered callback"""
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
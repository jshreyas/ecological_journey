"""
VideoState class for centralized state management of video data
"""

from typing import Any, Callable, Dict, List, Optional  # All used in type annotations

from utils.dialog_puns import generate_funny_title
from utils.user_context import User
from utils.utils_api import load_video, save_video_anchors


class VideoState:
    """Centralized state management for video data and refresh callbacks"""

    def __init__(self, video_id: str, user: User | None = None):
        self.video_id = video_id
        self.user = user
        self._video_data: Optional[Dict[str, Any]] = None
        self._refresh_callbacks: List[Callable] = []
        self.conversation: List[Dict[str, Any]] = []
        # 👇 controllers
        self._anchor_control_panel = None

        # 👇 anchors
        self.anchor_draft: list[dict] | None = None
        self._anchor_dirty: bool = False
        self.tabber = None
        self.init_anchor_draft()

    def add_anchor_at_time(self, t: float):
        t = int(t)

        self.anchor_draft.append(
            {
                "start": t,
                "title": generate_funny_title(),
            }
        )

        self._anchor_dirty = True
        self.refresh()

    def get_anchors(self) -> list[dict]:
        video = self.get_video()
        return video.get("anchors", [])

    def init_anchor_draft(self):
        if self.anchor_draft is None:
            source = self.get_anchors()
            self.anchor_draft = [a.copy() for a in source]
            self._anchor_dirty = False

    def reload_anchors(self):
        source = self.get_anchors()
        self.anchor_draft = [a.copy() for a in source]
        self._anchor_dirty = False

    def mark_anchor_dirty(self):
        self._anchor_dirty = True

    def is_anchor_dirty(self) -> bool:
        return self._anchor_dirty

    def save_anchors(self):
        video = self.get_video()
        video["anchors"] = sorted(self.anchor_draft, key=lambda a: a["start"])
        _ = save_video_anchors(video, self.user.token)
        self._anchor_dirty = False
        self.refresh()

    def get_anchor_control_panel(self):
        if self._anchor_control_panel is None:
            from pages.components.film.anchor_control_panel import AnchorControlPanel

            self._anchor_control_panel = AnchorControlPanel(self)
        return self._anchor_control_panel

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

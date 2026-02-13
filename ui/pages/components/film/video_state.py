"""
VideoState class for centralized state management of video data
"""

import re
from typing import Any, Callable, Dict, List, Optional  # All used in type annotations

from ui.data.crud import load_video
from ui.utils.dialog_puns import generate_funny_title
from ui.utils.user_context import User
from ui.utils.utils_api import save_video_metadata

TIME_PATTERN = re.compile(r"^(\d+:[0-5]\d:[0-5]\d|\d+:[0-5]\d)$")


class VideoState:
    """Centralized state management for video data and refresh callbacks"""

    def __init__(self, video_id: str, user: User | None = None):
        self.video_id = video_id
        self.user = user
        self._video_data: Optional[Dict[str, Any]] = None
        self._refresh_callbacks: List[Callable] = []
        self.conversation: List[Dict[str, Any]] = []

        self.anchor_draft: list[dict] | None = None
        self.clip_draft: list[dict] | None = None
        self.video_description_draft: str = None
        self._metadata_dirty: bool = False
        self.video_description_dirty: bool = False

        self.tabber = None
        self.reload_metadata()

    def add_anchor_at_time(self, t: float):
        t = int(t)

        self.anchor_draft.append(
            {
                "start": t,
                "title": generate_funny_title(),
                "_dirty": True,
            }
        )

        self._metadata_dirty = True
        self.refresh()

    def reload_metadata(self):
        self.anchor_draft = [a.copy() for a in self.get_anchors()]
        self.clip_draft = [c.copy() for c in self.get_clips()]
        self.video_description_draft = self.get_video_notes()
        self._metadata_dirty = False
        self.video_description_dirty = False

    def mark_metadata_dirty(self):
        self._metadata_dirty = True

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

    def get_video_notes(self) -> str:
        return self.get_video().get("notes", "")

    def get_anchors(self) -> list[dict]:
        return self.get_video().get("anchors", [])

    def save_video_metadata(self):
        video = self.get_video()
        duration = video.get("duration_seconds")

        # ---------- VIDEO LEVEL ----------
        notes = self.video_description_draft or ""
        video["notes"] = notes
        labels, partners = self._extract_labels_partners(notes)
        video["labels"] = labels
        video["partners"] = partners

        # ---------- ANCHORS ----------
        for anchor in self.anchor_draft:

            if "_time" in anchor:
                anchor["start"] = self._parse_timestamp(
                    anchor["_time"],
                    f"anchor '{anchor.get('title', '')}'",
                )

            if anchor.get("start") is not None:
                self._validate_anchor_time(anchor.get("start"), duration, f"anchor '{anchor.get('title', '')}'")

            desc = anchor.get("description", "")
            labels, partners = self._extract_labels_partners(desc)
            anchor["labels"] = labels
            anchor["partners"] = partners

            anchor.pop("_time", None)
            anchor.pop("_dirty", None)
            anchor.pop("_type", None)

        video["anchors"] = sorted(
            self.anchor_draft,
            key=lambda a: a.get("start", 0),
        )

        # ---------- CLIPS ----------
        for clip in self.clip_draft:

            context = f"clip '{clip.get('title', '')}'"

            if "_time" in clip:
                clip["start"] = self._parse_timestamp(clip["_time"], f"{context} start")

            if "_end_time" in clip:
                clip["end"] = self._parse_timestamp(clip["_end_time"], f"{context} end")

            start = clip.get("start")
            end = clip.get("end")

            if start is not None and end is not None:
                self._validate_clip_times(start, end, duration, context)

            desc = clip.get("description", "")
            labels, partners = self._extract_labels_partners(desc)
            clip["labels"] = labels
            clip["partners"] = partners

            clip.pop("_time", None)
            clip.pop("_end_time", None)
            clip.pop("_dirty", None)
            clip.pop("_type", None)

        video["clips"] = self.clip_draft

        # ---------- SAVE ----------
        _ = save_video_metadata(video, self.user.token)

        # Reset dirty flags
        self._metadata_dirty = False
        self.video_description_dirty = False

        for anchor in self.anchor_draft:
            anchor["_dirty"] = False

        for clip in self.clip_draft:
            clip["_dirty"] = False

        self.refresh()

    def _parse_timestamp(self, value: str, context: str) -> int:
        if not isinstance(value, str) or not TIME_PATTERN.fullmatch(value):
            raise ValueError(f"Invalid time format for {context}: '{value}'. " "Expected mm:ss or hh:mm:ss")

        parts = list(map(int, value.split(":")))

        if len(parts) == 2:
            minutes, seconds = parts
            return minutes * 60 + seconds

        if len(parts) == 3:
            hours, minutes, seconds = parts
            return hours * 3600 + minutes * 60 + seconds

        raise ValueError(f"Invalid time format for {context}: '{value}'")

    def _extract_labels_partners(self, text: str):
        import re

        LABEL_REGEX = re.compile(r"#([^\s#]+)")
        PARTNER_REGEX = re.compile(r"@([^\s#]+)")

        return (
            list(set(LABEL_REGEX.findall(text or ""))),
            list(set(PARTNER_REGEX.findall(text or ""))),
        )

    def _validate_clip_times(self, start: int, end: int, duration: int, context: str):
        if end <= start:
            raise ValueError(f"{context}: end time must be greater than start time")

        if duration is not None and end > duration:
            raise ValueError(f"{context}: end time exceeds video duration")

    def _validate_anchor_time(self, start: int, duration: int, context: str):

        if duration is not None and start > duration:
            raise ValueError(f"{context}: start time exceeds video duration")

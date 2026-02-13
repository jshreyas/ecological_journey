"""
VideoState class for centralized state management of video data
"""

from typing import Any, Callable, Dict, List, Optional  # All used in type annotations

from ui.data.crud import load_video
from ui.utils.dialog_puns import generate_funny_title
from ui.utils.user_context import User
from ui.utils.utils_api import save_video_metadata


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

    def save_anchors(self):
        video = self.get_video()

        video["anchors"] = sorted(
            self.anchor_draft,
            key=lambda a: a["start"],
        )

        # IMPORTANT: remove unrelated embedded fields
        video.pop("clips", None)

        _ = save_video_metadata(video, self.user.token)

        self._metadata_dirty = False
        self.refresh()

    # TODO: replace this to do a single metadata save
    def save_video_description(self, video_metadata: dict):
        video = self.get_video()
        video["notes"] = video_metadata.get("notes", "")
        video["partners"] = video_metadata.get("partners", [])
        video["labels"] = video_metadata.get("labels", [])
        video.pop("clips")
        video.pop("anchors")
        _ = save_video_metadata(video, self.user.token)
        self.refresh()
        from re import compile

        LABEL_REGEX = compile(r"#([^\s#]+)")
        PARTNER_REGEX = compile(r"@([^\s#]+)")

        video = self.get_video()

        # ---------- VIDEO LEVEL ----------
        notes = self.video_description_draft or ""
        video["notes"] = notes
        video["labels"] = list(set(LABEL_REGEX.findall(notes)))
        video["partners"] = list(set(PARTNER_REGEX.findall(notes)))

        # ---------- ANCHORS ----------
        cleaned_anchors = []
        for anchor in self.anchor_draft:

            try:
                m, s = anchor["_time"].split(":")
                start = int(m) * 60 + int(s)
            except Exception:
                raise ValueError(f"Invalid time format for anchor '{anchor.get('_time', '')}'")

            desc = anchor.get("description", "")

            cleaned_anchors.append(
                {
                    "start": start,
                    "title": anchor.get("title", ""),
                    "description": desc,
                    "labels": list(set(LABEL_REGEX.findall(desc))),
                    "partners": list(set(PARTNER_REGEX.findall(desc))),
                }
            )

        video["anchors"] = sorted(cleaned_anchors, key=lambda a: a["start"])

        # ---------- CLIPS ----------
        cleaned_clips = []
        for clip in self.clip_draft:

            try:
                m, s = clip["_time"].split(":")
                start = int(m) * 60 + int(s)
            except Exception:
                raise ValueError(f"Invalid start time format for clip '{clip.get('_time', '')}'")

            try:
                m, s = clip["_end_time"].split(":")
                end = int(m) * 60 + int(s)
            except Exception:
                raise ValueError(f"Invalid end time format for clip '{clip.get('_end_time', '')}'")

            desc = clip.get("description", "")

            cleaned_clips.append(
                {
                    "start": start,
                    "end": end,
                    "description": desc,
                    "labels": list(set(LABEL_REGEX.findall(desc))),
                    "partners": list(set(PARTNER_REGEX.findall(desc))),
                }
            )

        video["clips"] = cleaned_clips

        # ---------- SAVE ----------
        _ = save_video_metadata(video, self.user.token)

        self._metadata_dirty = False
        self.refresh()

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
        import re

        LABEL_REGEX = re.compile(r"#([^\s#]+)")
        PARTNER_REGEX = re.compile(r"@([^\s#]+)")

        video = self.get_video()

        # ---------- VIDEO LEVEL ----------
        notes = self.video_description_draft or ""
        video["notes"] = notes
        video["labels"] = list(set(LABEL_REGEX.findall(notes)))
        video["partners"] = list(set(PARTNER_REGEX.findall(notes)))

        # ---------- ANCHORS ----------
        for anchor in self.anchor_draft:

            # Convert time
            if "_time" in anchor:
                try:
                    m, s = anchor["_time"].split(":")
                    anchor["start"] = int(m) * 60 + int(s)
                except Exception:
                    raise ValueError(f"Invalid time format for anchor '{anchor.get('_time', '')}'")

            # Parse labels / partners
            desc = anchor.get("description", "")
            anchor["labels"] = list(set(LABEL_REGEX.findall(desc)))
            anchor["partners"] = list(set(PARTNER_REGEX.findall(desc)))

            # Clean UI-only fields
            anchor.pop("_time", None)
            anchor.pop("_dirty", None)
            anchor.pop("_type", None)

        video["anchors"] = sorted(
            self.anchor_draft,
            key=lambda a: a.get("start", 0),
        )

        # ---------- CLIPS ----------
        for clip in self.clip_draft:

            # Convert start
            if "_time" in clip:
                try:
                    m, s = clip["_time"].split(":")
                    clip["start"] = int(m) * 60 + int(s)
                except Exception:
                    raise ValueError(f"Invalid start time format for clip '{clip.get('_time', '')}'")

            # Convert end
            if "_end_time" in clip:
                try:
                    m, s = clip["_end_time"].split(":")
                    clip["end"] = int(m) * 60 + int(s)
                except Exception:
                    raise ValueError(f"Invalid end time format for clip '{clip.get('_end_time', '')}'")

            # Parse labels / partners
            desc = clip.get("description", "")
            clip["labels"] = list(set(LABEL_REGEX.findall(desc)))
            clip["partners"] = list(set(PARTNER_REGEX.findall(desc)))

            # Clean UI-only fields
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

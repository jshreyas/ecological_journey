"""
MetaforgeTab - Component for bulk editing video metadata
Handles the metaforge functionality for bulk editing
"""

import json
import uuid
from typing import Callable

from log import log
from nicegui import ui
from utils.dialog_puns import generate_funny_title
from utils.user_context import User
from utils.utils_api import save_video_metadata

from .video_state import VideoState


class MetaforgeTab:
    """Component for bulk editing video metadata"""

    def __init__(self, video_state: VideoState, user: User | None = None, on_publish: Callable = None):
        self.video_state = video_state
        self.user = user
        self.on_publish = on_publish
        self.container = None
        self.editor_container = {"ref": None}
        self.diff_area = None
        self.confirm_dialog = None
        self.state = {"latest_cleaned": None}

        # Register for video state refresh notifications
        self.video_state.add_refresh_callback(self.refresh)

    def create_tab(self, container):
        """Create the metaforge tab UI"""
        self.container = container
        self.refresh()

    def refresh(self):
        """Refresh the metaforge tab with current video data"""
        if not self.container:
            return

        self.container.clear()
        with self.container:
            self._create_metaforge_ui()

    def _create_metaforge_ui(self):
        """Create the metaforge editing UI"""
        video = self.video_state.get_video()
        if not video:
            ui.label("No video data available")
            return

        # Create confirm dialog
        self.confirm_dialog = ui.dialog()
        with self.confirm_dialog:
            with ui.card().classes("max-w-xl"):
                ui.label("📝 Review Changes").classes("text-lg font-bold")
                self.diff_area = ui.markdown("").classes("text-sm text-left whitespace-pre-wrap max-h-80 overflow-auto")
                with ui.row().classes("justify-end w-full"):
                    ui.button(icon="close", on_click=self.confirm_dialog.close)
                    ui.button(
                        icon="save",
                        color="primary",
                        on_click=lambda: self._finalize_save(),
                    )

        # Create JSON schema
        json_schema = {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "labels": {"type": "array", "items": {"type": "string"}, "default": []},
                "partners": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                },
                "clips": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "clip_id": {"type": "string", "default": ""},
                            "start": {
                                "type": "string",
                                "pattern": r"^(\d+:[0-5]\d:[0-5]\d|\d+:[0-5]\d)$",
                                "description": "Format: mm:ss or hh:mm:ss",
                            },
                            "end": {
                                "type": "string",
                                "pattern": r"^(\d+:[0-5]\d:[0-5]\d|\d+:[0-5]\d)$",
                                "description": "Format: mm:ss or hh:mm:ss",
                            },
                            "speed": {
                                "type": "number",
                                "minimum": 0.25,
                                "maximum": 2.0,
                                "default": 2.0,
                            },
                            "title": {"type": "string", "default": ""},
                            "labels": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                            },
                            "partners": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                            },
                        },
                        "required": [
                            "start",
                            "end",
                            "title",
                            "labels",
                            "partners",
                            "speed",
                        ],
                    },
                },
                "anchors": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "clip_id": {"type": "string", "default": ""},
                            "start": {  # TODO: change this to string with timestamp format
                                "type": "number",
                                # "pattern": r"^(\d+:[0-5]\d:[0-5]\d|\d+:[0-5]\d)$",
                                "description": "Format: mm:ss or hh:mm:ss",
                            },
                            "title": {"type": "string", "default": ""},
                            "labels": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                            },
                        },
                        "required": [
                            "start",
                            "title",
                            "labels",
                        ],
                    },
                },
            },
            "required": ["description", "labels", "partners", "clips", "anchors"],
        }

        # Create JSON editor
        editor = ui.json_editor(
            {"content": {"json": self._extract_editable_video_data(video)}},
            schema=json_schema,
        ).classes("w-full h-full mt-0 mb-0")

        # Store editor reference
        self.editor_container["ref"] = editor

        # Action buttons
        if self.user:
            ui.button(icon="save", on_click=self._get_data).classes("absolute bottom-0 right-0")
            ui.button(icon="add", on_click=self._add_clip).classes("absolute bottom-0 left-0")

    def _extract_editable_video_data(self, full_video: dict) -> dict:
        """Extract editable video data for the JSON editor"""
        return {
            "description": full_video.get("notes", ""),
            "labels": full_video.get("labels", []),
            "partners": full_video.get("partners", []),
            "anchors": full_video.get("anchors", []),
            "clips": [
                {
                    "clip_id": clip["clip_id"],
                    "start": self._seconds_to_timestamp(clip["start"]),
                    "end": self._seconds_to_timestamp(clip["end"]),
                    "speed": clip.get("speed", 1.0),
                    "title": clip["title"],
                    "description": clip.get("description", ""),
                    "labels": clip.get("labels", []),
                    "partners": clip.get("partners", []),
                }
                for clip in full_video.get("clips", [])
            ],
        }

    def _seconds_to_timestamp(self, seconds: int | float) -> str:
        """Convert seconds to timestamp format"""
        seconds = int(seconds)
        minutes, sec = divmod(seconds, 60)
        return f"{minutes}:{sec:02d}"

    def _parse_timestamp(self, ts: str | int | float) -> int:
        """Parse timestamp to seconds"""
        if isinstance(ts, (int, float)):
            return int(ts)
        parts = [int(p) for p in ts.strip().split(":")]
        if len(parts) == 1:
            return parts[0]
        elif len(parts) == 2:
            minutes, seconds = parts
            return minutes * 60 + seconds
        elif len(parts) == 3:
            hours, minutes, seconds = parts
            return hours * 3600 + minutes * 60 + seconds
        raise ValueError(f"Invalid timestamp format: {ts}")

    def _validate_film_data(self, video: dict, video_duration: int) -> dict:
        """Validate film data and return cleaned version"""
        if not isinstance(video.get("labels", []), list):
            raise ValueError("Video.labels must be a list of strings")
        if not isinstance(video.get("partners", []), list):
            raise ValueError("Video.partners must be a list of strings")

        cleaned_clips = []

        for clip in video.get("clips", []):
            try:
                start = self._parse_timestamp(clip["start"])
                end = self._parse_timestamp(clip["end"])
            except Exception:
                raise ValueError(
                    f"Clip timestamps must be in mm:ss or hh:mm:ss format: {clip.get('start')} - {clip.get('end')}"
                )

            if start < 0 or end < 0:
                raise ValueError("Start and end times must be non-negative")
            if end <= start:
                raise ValueError(f"Clip end ({end}) must be after start ({start})")
            if end > video_duration:
                raise ValueError(f"Clip end ({end}) exceeds video duration ({video_duration} seconds)")

            speed = float(clip.get("speed", 2.0))
            if not (0.25 <= speed <= 2.0):
                raise ValueError(f"Invalid speed: {speed} (must be 0.25–2.0)")

            if not isinstance(clip.get("labels", []), list):
                raise ValueError("Clip.labels must be a list of strings")
            if not isinstance(clip.get("partners", []), list):
                raise ValueError("Clip.partners must be a list of strings")

            # Build cleaned clip
            clip_id = clip.get("clip_id", str(uuid.uuid4()))
            cleaned_clip = {
                "clip_id": clip_id,
                "start": start,
                "end": end,
                "speed": speed,
                "title": clip.get("title", ""),
                "description": clip.get("description", ""),
                "labels": clip.get("labels", []),
                "partners": clip.get("partners", []),
            }
            cleaned_clips.append(cleaned_clip)

        return {
            "description": video.get("description", ""),
            "labels": video.get("labels", []),
            "partners": video.get("partners", []),
            "clips": cleaned_clips,
            "anchors": video.get("anchors", []),
        }

    def _dict_diff(self, d1, d2, path=""):
        """Generate diff between two dictionaries"""
        diffs = []
        keys = set(d1.keys()) | set(d2.keys())

        for key in keys:
            v1 = d1.get(key, "__MISSING__")
            v2 = d2.get(key, "__MISSING__")
            current_path = f"{path}.{key}" if path else key

            if isinstance(v1, dict) and isinstance(v2, dict):
                diffs.extend(self._dict_diff(v1, v2, current_path))
            elif isinstance(v1, list) and isinstance(v2, list):
                min_len = min(len(v1), len(v2))
                for i in range(min_len):
                    if isinstance(v1[i], dict) and isinstance(v2[i], dict):
                        diffs.extend(self._dict_diff(v1[i], v2[i], f"{current_path}[{i}]"))
                    elif v1[i] != v2[i]:
                        diffs.append((f"{current_path}[{i}]", v1[i], v2[i]))
                if len(v1) != len(v2):
                    diffs.append((current_path, v1, v2))
            elif v1 != v2:
                diffs.append((current_path, v1, v2))
        return diffs

    def _try_make_set(self, lst):
        """Try to convert list to set, return None if not hashable"""
        try:
            return set(lst)
        except TypeError:
            return None

    def _format_value(self, v):
        """Format values for display"""
        if isinstance(v, list):
            return ", ".join(f'"{str(x)}"' for x in v)
        elif isinstance(v, str):
            return f'"{v}"'
        else:
            return str(v)

    def _summarize_dict_diff(self, d1, d2):
        """Summarize dictionary differences"""
        diffs = self._dict_diff(d1, d2)
        if not diffs:
            return "✅ No changes detected."

        summary = []
        clip_changes = {}
        unordered_keys = {"labels", "partners"}

        # Extract clip titles from the new data (d2)
        clip_titles = {i: clip.get("title", f"Clip {i}") for i, clip in enumerate(d2.get("clips", []))}

        # Detect new/deleted clips by clip_id or clipid
        old_clips = {
            clip.get("clip_id", clip.get("clipid", f"Clip{i}")): clip for i, clip in enumerate(d1.get("clips", []))
        }
        new_clips = {
            clip.get("clip_id", clip.get("clipid", f"Clip{i}")): clip for i, clip in enumerate(d2.get("clips", []))
        }

        added_clip_ids = set(new_clips) - set(old_clips)
        removed_clip_ids = set(old_clips) - set(new_clips)

        if added_clip_ids:
            summary.append("➕ **Added Clips:**")
            for cid in added_clip_ids:
                title = new_clips[cid].get("title", cid)
                summary.append(f"    • {title}")

        if removed_clip_ids:
            summary.append("❌ Removed Clips:")
            for cid in removed_clip_ids:
                title = old_clips[cid].get("title", cid)
                summary.append(f"    • {title}")

        # Process clip-level diffs
        for path, old, new in diffs:
            if path.startswith("clips["):
                clip_index = int(path.split("[")[1].split("]")[0])
                field = path.split("].", 1)[-1]

                if field == "title":
                    clip_titles[clip_index] = new

                clip_changes.setdefault(clip_index, []).append((field, old, new))

        # Filter out clip-level diffs
        filtered_diffs = [diff for diff in diffs if not diff[0].startswith("clips[") and diff[0] != "clips"]

        video_changes = []

        for path, old, new in filtered_diffs:
            field = path.split(".")[-1]

            if old == "__MISSING__":
                video_changes.append(f"➕ `{path}`: {self._format_value(new)}")
            elif new == "__MISSING__":
                video_changes.append(f"❌ `{path}`: {self._format_value(old)}")
            elif isinstance(old, list) and isinstance(new, list) and field in unordered_keys:
                old_set = self._try_make_set(old)
                new_set = self._try_make_set(new)

                if old_set is not None and new_set is not None:
                    added = new_set - old_set
                    removed = old_set - new_set

                    if added:
                        added_str = ", ".join(f'"{x}"' for x in sorted(added))
                        video_changes.append(f"➕ `{path}`: added {added_str}")
                    if removed:
                        removed_str = ", ".join(f'"{x}"' for x in sorted(removed))
                        video_changes.append(f"❌ `{path}`: removed {removed_str}")
                else:
                    if old != new:
                        video_changes.append(f"🔄 `{path}`: {self._format_value(old)} → {self._format_value(new)}")
            else:
                video_changes.append(f"🔄 `{path}`: {self._format_value(old)} → {self._format_value(new)}")

        if video_changes:
            summary.append("🎞️ **Video Changes:**")
            summary.extend(video_changes)

        # Process clip changes grouped by clip index
        for idx, changes in sorted(clip_changes.items()):
            title = clip_titles.get(idx, f"Clip {idx}")
            summary.append(f"\n🎬 **Changes in Clip '{title}':**")
            for field, old, new in changes:
                if old == "__MISSING__":
                    summary.append(f"➕ `{field}`: {self._format_value(new)}")
                elif new == "__MISSING__":
                    summary.append(f"❌ `{field}`: {self._format_value(old)}")
                elif isinstance(old, list) and isinstance(new, list) and field in unordered_keys:
                    old_set = self._try_make_set(old)
                    new_set = self._try_make_set(new)

                    if old_set is not None and new_set is not None:
                        added = new_set - old_set
                        removed = old_set - new_set

                        if added:
                            added_str = ", ".join(f'"{x}"' for x in sorted(added))
                            summary.append(f"➕ `{field}`: added {added_str}")
                        if removed:
                            removed_str = ", ".join(f'"{x}"' for x in sorted(removed))
                            summary.append(f"❌ `{field}`: removed {removed_str}")
                    else:
                        if old != new:
                            summary.append(f"🔄 `{field}`: {self._format_value(old)} → {self._format_value(new)}")
                else:
                    summary.append(f"🔄 `{field}`: {self._format_value(old)} → {self._format_value(new)}")

        return "\n".join(summary)

    def _extract_editable_fields(self, video: dict) -> dict:
        """Extract editable fields from video data"""
        return {
            "description": video.get("notes", ""),
            "labels": video.get("labels", []),
            "partners": video.get("partners", []),
            "clips": [
                {
                    "clip_id": clip["clip_id"],
                    "start": clip["start"],
                    "end": clip["end"],
                    "speed": clip["speed"],
                    "title": clip["title"],
                    "description": clip.get("description", ""),
                    "labels": clip.get("labels", []),
                    "partners": clip.get("partners", []),
                }
                for clip in video.get("clips", [])
            ],
        }

    # TODO: account for saving anchors as well
    async def _get_data(self):
        """Get data from JSON editor and validate"""
        editor = self.editor_container["ref"]
        if not editor:
            ui.notify("❌ Editor not initialized", type="negative")
            return

        raw_data = await editor.run_editor_method("get")

        # Normalize input
        if "json" in raw_data:
            data = raw_data["json"]
        elif "text" in raw_data:
            try:
                data = json.loads(raw_data["text"])
            except json.JSONDecodeError as ex:
                ui.notify(f"❌ Invalid JSON format: {ex}", type="negative")
                return
        else:
            ui.notify("❌ Unexpected editor return format", type="negative")
            return

        try:
            video = self.video_state.get_video()
            cleaned = self._validate_film_data(data, video.get("duration_seconds"))
        except Exception as ex:
            ui.notify(f"❌ Validation error: {ex}", type="negative")
            return

        for key in ["video_id", "youtube_url", "title", "date", "duration_seconds"]:
            cleaned[key] = video.get(key)

        # Extract and compare editable fields only
        delta = self._dict_diff(self._extract_editable_fields(video), self._extract_editable_fields(cleaned))
        summary = self._summarize_dict_diff(
            self._extract_editable_fields(video), self._extract_editable_fields(cleaned)
        )

        if not delta:
            ui.notify("✅ No changes detected.", type="info")
            return

        # Save cleaned data for confirm step
        self.state["latest_cleaned"] = cleaned

        self.diff_area.set_content(summary)
        self.confirm_dialog.open()

    def _finalize_save(self):
        """Finalize the save operation"""
        self.confirm_dialog.close()
        log.info(f"Finalizing save...: {self.state['latest_cleaned']}")
        token = self.user.token if self.user else None
        success = save_video_metadata(self.state["latest_cleaned"], token)
        if success:
            ui.notify("✅ Filmdata published", type="positive")
            # Clear the state to prevent cumulative delta tracking
            self.state["latest_cleaned"] = None
            # Refresh video state and notify all components
            self.video_state.refresh()
        else:
            ui.notify("❌ Failed to publish filmdata", type="negative")

    def _add_clip(self):
        """Add a new clip to the JSON editor"""
        new_clip = {
            "clip_id": str(uuid.uuid4()),
            "start": "00:00",
            "end": "00:00",
            "title": generate_funny_title(),
            "description": "",
            "labels": [],
            "partners": [],
            "speed": 2.0,
        }

        async def inject():
            editor = self.editor_container["ref"]
            if not editor:
                ui.notify("❌ Editor not initialized", type="negative")
                return
            current = await editor.run_editor_method("get")
            content = json.loads(current.get("text")) if isinstance(current.get("text"), str) else current.get("json")
            content.setdefault("clips", []).append(new_clip)
            await editor.run_editor_method("set", {"json": content})
            self.container.scroll_to(percent=100)

        ui.timer(0.1, inject, once=True)

    def get_video_data(self):
        """Get the current video data"""
        return self.video_state.get_video()

    def _remove_clip(self, clip_id):
        """Remove a clip from the video"""
        video_data = self.get_video_data()
        if video_data and "clips" in video_data:
            video_data["clips"] = [c for c in video_data["clips"] if c.get("clip_id") != clip_id]
            ui.notify("✅ Clip removed successfully", type="positive")

    def _update_clip(self, clip_data):
        """Update a clip in the video"""
        video_data = self.get_video_data()
        if video_data and "clips" in video_data:
            for i, clip in enumerate(video_data["clips"]):
                if clip.get("clip_id") == clip_data.get("clip_id"):
                    video_data["clips"][i] = clip_data
                    break
            ui.notify("✅ Clip updated successfully", type="positive")

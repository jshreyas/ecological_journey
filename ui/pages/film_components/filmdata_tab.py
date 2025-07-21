"""
FilmdataTab - Component for editing film metadata
Handles the film metadata editing functionality
"""

from typing import Callable

from nicegui import app, ui
from utils.utils_api import save_video_metadata

from .video_state import VideoState


class FilmdataTab:
    """Component for editing film metadata"""

    def __init__(self, video_state: VideoState, on_publish: Callable = None):
        self.video_state = video_state
        self.on_publish = on_publish
        self.container = None
        self.chips_list = []
        self.notes_input = None

        # Register for video state refresh notifications
        self.video_state.add_refresh_callback(self.refresh)

    def create_tab(self, container):
        """Create the filmdata tab UI"""
        self.container = container
        self.refresh()

    def refresh(self):
        """Refresh the filmdata tab with current video data"""
        if not self.container:
            return

        self.container.clear()
        with self.container:
            self._create_filmdata_ui()

    def _create_filmdata_ui(self):
        """Create the filmdata editing UI"""
        video = self.video_state.get_video()
        if not video:
            ui.label("No video data available")
            return

        # Chips input for @partners and #labels
        chips_input_ref, chips_list, chips_error, chips_container = self._create_chips_input(
            [f"@{p}" for p in video.get("partners", [])] + [f"#{label}" for label in video.get("labels", [])]
        )
        self.chips_list = chips_list

        # Notes textarea
        notes_input = ui.textarea("Notes", value=video.get("notes", "")).props("rows=4").classes("w-full")
        self.notes_input = notes_input

        # Save button
        with ui.row().classes("justify-end gap-2 mt-4"):
            ui.button(icon="save", on_click=lambda: self._handle_save()).props("color=primary")

    def _create_chips_input(self, initial=None):
        """Create chips input for partners and labels"""
        initial = initial or []
        chips_list = initial.copy()
        container = ui.row().classes("gap-2")
        input_ref = ui.input("Add @partner or #label").classes("w-full").props("dense")
        error_label = ui.label().classes("text-red-500 text-xs")

        def add_chip():
            val = input_ref.value.strip()
            if not val:
                return
            if not (val.startswith("@") or val.startswith("#")):
                error_label.text = "Start with @ for partners or # for labels"
                return
            if val in chips_list:
                error_label.text = "Already added"
                return
            error_label.text = ""
            chips_list.append(val)
            with container:
                ui.chip(
                    val,
                    icon="person" if val.startswith("@") else "label",
                    color="secondary" if val.startswith("@") else "primary",
                    removable=True,
                ).on("remove", lambda e, v=val: chips_list.remove(v))
            input_ref.value = ""

        input_ref.on("keydown.enter", add_chip)
        with input_ref.add_slot("append"):
            ui.button(icon="add", on_click=add_chip).props("round dense flat")
        # Render initial chips
        with container:
            for val in chips_list:
                ui.chip(
                    val,
                    icon="person" if val.startswith("@") else "label",
                    color="secondary" if val.startswith("@") else "primary",
                    removable=True,
                ).on("remove", lambda e, v=val: chips_list.remove(v))
        return input_ref, chips_list, error_label, container

    def _handle_save(self):
        """Handle save operation"""
        if self.on_publish:
            # Extract data from UI
            partners_list = [c[1:] for c in self.chips_list if c.startswith("@")]
            labels_list = [c[1:] for c in self.chips_list if c.startswith("#")]
            notes = self.notes_input.value if self.notes_input else ""

            metadata = {
                "partners": partners_list,
                "labels": labels_list,
                "notes": notes,
            }
            self.on_publish(metadata)
        else:
            # Default save behavior
            token = app.storage.user.get("token")
            if not token:
                ui.notify("❌ Authentication required", type="negative")
                return

            try:
                # Extract data from UI
                partners_list = [c[1:] for c in self.chips_list if c.startswith("@")]
                labels_list = [c[1:] for c in self.chips_list if c.startswith("#")]
                notes = self.notes_input.value if self.notes_input else ""

                # Get current video data
                video = self.video_state.get_video()
                if not video:
                    ui.notify("❌ No video data available", type="negative")
                    return

                # Prepare metadata for save
                metadata = video.copy()
                metadata.update({"partners": partners_list, "labels": labels_list, "notes": notes})

                success = save_video_metadata(metadata, token)
                if success:
                    ui.notify("✅ Filmdata saved successfully", type="positive")
                    self.video_state.refresh()
                else:
                    ui.notify("❌ Failed to save filmdata", type="negative")
            except Exception as e:
                ui.notify(f"❌ Error saving filmdata: {e}", type="negative")

    def handle_publish(self, video_metadata=None):
        """Handle publish operation"""
        if self.on_publish:
            self.on_publish(video_metadata)
        else:
            # Default publish behavior
            token = app.storage.user.get("token")
            if not token:
                ui.notify("❌ Authentication required", type="negative")
                return

            try:
                video = self.video_state.get_video()
                if not video:
                    ui.notify("❌ No video data available", type="negative")
                    return

                # Merge with required fields from the loaded video
                for key in [
                    "video_id",
                    "youtube_url",
                    "title",
                    "date",
                    "duration_seconds",
                ]:
                    video_metadata[key] = video.get(key)
                # Preserve existing clips!
                video_metadata["clips"] = video.get("clips", [])

                success = save_video_metadata(video_metadata, token)
                if success:
                    ui.notify("✅ Filmdata published", type="positive")
                else:
                    ui.notify("❌ Failed to publish filmdata", type="negative")
            except Exception as e:
                ui.notify(f"❌ Error: {e}", type="negative")

    def get_video_data(self):
        """Get the current video data"""
        return self.video_state.get_video()

    def _reset_fields(self):
        """Reset fields to original values"""
        video_data = self.get_video_data()
        if video_data:
            self.chips_list = [f"@{p}" for p in video_data.get("partners", [])] + [
                f"#{label}" for label in video_data.get("labels", [])
            ]
            if self.notes_input:
                self.notes_input.value = video_data.get("notes", "")

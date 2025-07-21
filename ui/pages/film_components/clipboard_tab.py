"""
ClipboardTab - Component for displaying and managing clips
Handles the clipboard functionality for viewing and managing clips
"""

from typing import Callable

from nicegui import ui
from utils.utils import format_time

from .video_state import VideoState


class ClipboardTab:
    """Component for displaying and managing clips"""

    def __init__(
        self,
        video_state: VideoState,
        on_edit_clip: Callable = None,
        on_play_clip: Callable = None,
        on_share_clip: Callable = None,
    ):
        self.video_state = video_state
        self.on_edit_clip = on_edit_clip
        self.on_play_clip = on_play_clip
        self.on_share_clip = on_share_clip
        self.container = None

        # Register for video state refresh notifications
        self.video_state.add_refresh_callback(self.refresh)

    def create_tab(self, container, clip_id=None):
        """Create the clipboard tab UI"""
        self.container = container
        self.refresh(clip_id)

    def refresh(self, clip_id=None):
        """Refresh the clipboard tab with current video data"""
        if not self.container:
            return

        self.container.clear()
        with self.container:
            self._create_clipboard_ui(clip_id)

    def _create_clipboard_ui(self, clip_id=None):
        """Create the clipboard UI"""
        video = self.video_state.get_video()
        if not video:
            ui.label("No video data available")
            return

        clips = video.get("clips", [])
        if not clips:
            ui.label("📭 No clips for this film yet.").classes("text-sm text-gray-500")
            return

        # Display clips using the original layout
        for clip in clips:
            clip["video_id"] = self.video_state.video_id  # Ensure video_id is present
            if clip_id and clip["clip_id"] == clip_id:
                self._add_clip_card(clip, highlight=True, autoplay=True, video_data=video)
            else:
                self._add_clip_card(clip, video_data=video)

    def _add_clip_card(self, clip, highlight=False, autoplay=False, video_data=None):
        """Add a clip card to the clipboard using the original layout"""
        # Use provided video_data or fall back to global video
        if video_data is None:
            video_data = self.video_state.get_video()

        highlight_class = " border-2 border-blue-500" if highlight else ""
        card_classes = f"p-2 flex flex-col justify-between max-w-full overflow-hidden{highlight_class}"
        with ui.card().classes(card_classes):
            with ui.column().classes("w-full gap-2"):
                ui.label(clip["title"]).classes("font-medium text-sm truncate")
                with ui.row().classes("w-full gap-2 justify-between"):
                    start_time = format_time(clip.get("start", 0))
                    end_time = format_time(clip.get("end", 0))
                    ui.label(f"⏱ {start_time} - {end_time}").classes("text-xs")
                    ui.label(f"{format_time(clip.get('end', 0) - clip.get('start', 0))}").classes("text-xs")

            # --- Partners (clip in black, video in primary blue) ---
            partners = clip.get("partners", [])
            video_partners = video_data.get("partners", [])
            partners_html = ""
            if partners:
                partners_html = ", ".join(f"<span style='color:black'>{p}</span>" for p in partners)
            if video_partners:
                if partners_html:
                    partners_html += ", "
                partners_html += ", ".join(f"<span style='color:var(--q-primary)'>{p}</span>" for p in video_partners)
            if not partners_html:
                partners_html = "No partners"
            ui.html(f"🎭 {partners_html}").classes("text-xs")

            # --- Labels (clip in black, video in primary blue) ---
            labels = clip.get("labels", [])
            video_labels = video_data.get("labels", [])
            labels_html = ""
            if labels:
                labels_html = ", ".join(f"<span style='color:black'>{label}</span>" for label in labels)
            if video_labels:
                if labels_html:
                    labels_html += ", "
                labels_html += ", ".join(
                    f"<span style='color:var(--q-primary)'>{label}</span>" for label in video_labels
                )
            if not labels_html:
                labels_html = "No labels"
            ui.html(f"🏷️ {labels_html}").classes("text-xs")

            button_group_classes = (
                "w-full flex-wrap shadow-none border-none items-center " "max-w-full justify-center gap-2"
            )
            with ui.button_group().classes(button_group_classes):
                for icon, color, tooltip, handler in [
                    (
                        "play_arrow",
                        "primary",
                        "Play",
                        lambda: self._handle_play_clip(clip),
                    ),
                    ("edit", "secondary", "Edit", lambda: self._handle_edit_clip(clip)),
                    ("share", "accent", "Share", lambda: self._handle_share_clip(clip)),
                ]:
                    ui.button(icon=icon, on_click=handler).props(f"flat dense color={color}").tooltip(tooltip).classes(
                        "flex-1 min-w-0"
                    )

            # Optionally, auto-play the clip if requested
            if autoplay:
                self._handle_play_clip(clip)

    def _handle_edit_clip(self, clip):
        """Handle edit clip action"""
        if self.on_edit_clip:
            self.on_edit_clip(clip)

    def _handle_play_clip(self, clip):
        """Handle play clip action"""
        if self.on_play_clip:
            self.on_play_clip(clip)

    def _handle_share_clip(self, clip):
        """Handle share clip action"""
        if self.on_share_clip:
            self.on_share_clip(clip)

    def get_video_data(self):
        """Get the current video data"""
        return self.video_state.get_video()

    def get_clips(self):
        """Get clips from the current video"""
        video = self.video_state.get_video()
        return video.get("clips", []) if video else []

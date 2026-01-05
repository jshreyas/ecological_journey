import random

from nicegui import ui


class AnchorboardTab:

    def __init__(self, video_state, on_play_anchor):
        self.video_state = video_state
        self.on_play_anchor = on_play_anchor
        self.container = None

        # Register for video state refresh notifications
        self.video_state.add_refresh_callback(self.refresh)

    def create_tab(self, container):
        self.container = container
        self.refresh()

    def _create_anchorboard_ui(self):
        anchors = sorted(self.video_state.anchor_draft, key=lambda a: a["start"])

        with self.container:
            with ui.column().classes("w-full p-4 gap-4"):
                # ui.label("Anchors").classes("text-lg font-semibold")
                # ui.button(
                #     icon="edit",
                #     on_click=lambda: self.video_state.get_anchor_control_panel().open(),
                # ).props("outline")

                with ui.grid(columns=4).classes("w-full gap-4"):
                    for anchor in anchors:
                        self._render_anchor_tile(anchor)

    def refresh(self):
        """Refresh the clipboard tab with current video data"""
        if not self.container:
            return

        self.container.clear()
        with self.container:
            self._create_anchorboard_ui()

    def _render_anchor_tile(self, anchor):
        size_class = random.choice(
            [
                "col-span-1",
                "col-span-2",
            ]
        )

        with (
            ui.card()
            .classes(f"{size_class} cursor-pointer hover:shadow-lg transition")
            .on("click", lambda a=anchor: self.on_play_anchor(a["start"]))
        ):
            with ui.column().classes("gap-2"):
                # ui.label(anchor["title"]).classes("font-medium")

                ui.label(self._format_time(anchor["start"])).classes("text-sm text-gray-500")

                with ui.row().classes("gap-1"):
                    for label in anchor.get("labels", []):
                        ui.badge(label).classes("bg-primary text-white")

    @staticmethod
    def _format_time(seconds: int) -> str:
        m, s = divmod(int(seconds), 60)
        return f"{m}:{s:02d}"

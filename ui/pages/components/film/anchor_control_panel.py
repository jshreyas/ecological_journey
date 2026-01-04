from nicegui import ui


class AnchorControlPanel:
    def __init__(self, video_state):
        self.video_state = video_state
        self.dialog = None
        self.container = None

        # Register refresh callback
        self.video_state.add_refresh_callback(self.refresh)

    def open(self):
        if self.dialog:
            self.dialog.open()
            return

        self.dialog = ui.dialog().props("persistent")
        with self.dialog, ui.card().classes("w-[90vw] h-[80vh] p-4"):
            self._render()

        self.dialog.open()

    def refresh(self):
        """Re-render anchors from video_state.anchor_draft"""
        self.dialog = None

    def _render(self):
        ui.label("Anchor Control Panel").classes("text-lg font-semibold mb-2")
        # print("Rednering anchors:", self.video_state.anchor_draft)
        sorted_anchors = sorted(self.video_state.anchor_draft, key=lambda a: a["t"])
        for anchor in sorted_anchors:
            self._render_row(anchor)

        with ui.row().classes("justify-end gap-2"):
            ui.button("Cancel", on_click=self.dialog.close)

            save_btn = ui.button(
                "Save",
                on_click=self._save_and_close,
            ).props("color=black")

            save_btn.bind_enabled_from(
                self.video_state,
                "is_anchor_dirty",
            )

    def _render_row(self, anchor):
        with ui.row().classes("items-center gap-4"):
            ui.input(
                value=self._format_time(anchor["t"]),
                on_change=lambda e, a=anchor: self._update_time(a, e.value),
            ).classes("w-20")

            ui.input(
                value=anchor.get("title", ""),
                on_change=lambda e, a=anchor: a.__setitem__("title", e.value),
            ).classes("w-60")

            ui.input(
                value=", ".join(anchor.get("labels", [])),
                on_change=lambda e, a=anchor: self._update_labels(a, e.value),
            ).classes("w-60")

            ui.button(
                "🗑",
                on_click=lambda a=anchor: self._delete_anchor(a),
            ).props("flat dense")

    def _delete_anchor(self, anchor):
        self.video_state.anchor_draft.remove(anchor)
        self.video_state.mark_anchor_dirty()
        self.video_state.refresh()  # Trigger re-render via refresh callback

    def _update_time(self, anchor, value):
        try:
            m, s = value.split(":")
            anchor["t"] = int(m) * 60 + int(s)
            self.video_state.mark_anchor_dirty()
            self.video_state.refresh()
        except Exception:
            ui.notify("Invalid time format (mm:ss)", type="warning")

    def _update_labels(self, anchor, value):
        anchor["labels"] = [_.strip() for _ in value.split(",") if _.strip()]
        self.video_state.mark_anchor_dirty()
        self.video_state.refresh()

    def _format_time(self, t):
        m, s = divmod(t, 60)
        return f"{m}:{s:02d}"

    def _save_and_close(self):
        self.video_state.save_anchors()
        # self.dialog.close()
        ui.notify("Anchors saved", type="positive")

from nicegui import ui

SEED_ANCHORS = [
    {
        "id": "a1",
        "t": 423,  # 7:03
        "title": "Back entry attempt → reversal",
        "labels": ["#backentry"],
        "notes": "Not fully to back, resulted in reversal",
    },
    {
        "id": "a2",
        "t": 790,  # 13:10
        "title": "Clean back entry",
        "labels": ["#backentry"],
        "notes": "",
    },
    {
        "id": "a3",
        "t": 845,  # 14:05
        "title": "Back entry sequence",
        "labels": ["#backentry"],
        "notes": "",
    },
    {
        "id": "a4",
        "t": 1190,  # 19:50
        "title": "Dynamic scramble sequence",
        "labels": ["#backentry"],
        "notes": "Not a back take, but cool sequence",
    },
    {
        "id": "a5",
        "t": 2055,  # 34:15
        "title": "Back entry from transition",
        "labels": ["#backentry"],
        "notes": "",
    },
    {
        "id": "a6",
        "t": 2642,  # 44:02
        "title": "Late-round back entry",
        "labels": ["#backentry"],
        "notes": "",
    },
    {
        "id": "a7",
        "t": 2867,  # 47:47
        "title": "Final back entry attempt",
        "labels": ["#backentry"],
        "notes": "",
    },
]


class AnchorControlPanel:
    def __init__(self, video_state):
        self.video_state = video_state
        self.dialog = None
        self.draft_anchors = []

    def open(self):
        if self.dialog:
            self.dialog.open()
            return

        self.draft_anchors = [a.copy() for a in SEED_ANCHORS]

        self.dialog = ui.dialog().props("persistent")
        with self.dialog, ui.card().classes("w-[90vw] h-[80vh] p-4"):
            self._render()

        self.dialog.open()

    def _render(self):
        ui.label("Anchor Control Panel").classes("text-lg font-semibold mb-2")

        # Header
        with ui.row().classes("font-semibold gap-4"):
            ui.label("Time").classes("w-20")
            ui.label("Title").classes("w-60")
            ui.label("Labels").classes("w-60")
            ui.label("")

        ui.separator()

        # Rows
        for anchor in self.draft_anchors:
            self._render_row(anchor)

        ui.separator().classes("my-2")

        with ui.row().classes("justify-end gap-2"):
            ui.button("Cancel", on_click=self.dialog.close)
            ui.button("Save", on_click=self._save_and_close).props("color=black")

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
        self.draft_anchors.remove(anchor)
        self.dialog.close()
        self.dialog = None
        self.open()  # simple rerender for MVP

    def _update_time(self, anchor, value):
        try:
            m, s = value.split(":")
            anchor["t"] = int(m) * 60 + int(s)
        except Exception:
            ui.notify("Invalid time format (mm:ss)", type="warning")

    def _update_labels(self, anchor, value):
        anchor["labels"] = [_.strip() for _ in value.split(",") if _.strip()]

    def _format_time(self, t):
        m, s = divmod(t, 60)
        return f"{m}:{s:02d}"

    def _save_and_close(self):
        self.video_state.metadata["anchors"] = sorted(self.draft_anchors, key=lambda a: a["t"])
        self.dialog.close()
        ui.notify("Anchors saved", type="positive")

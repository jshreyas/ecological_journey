import random

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


class AnchorboardTab:

    def __init__(self, video_state, on_play_anchor):
        self.video_state = video_state
        self.on_play_anchor = on_play_anchor

    def create_tab(self, container):
        # anchors = self.video_state.metadata.get("anchors", [])
        anchors = SEED_ANCHORS

        with container:
            with ui.column().classes("w-full p-4 gap-4"):
                # ui.label("Anchors").classes("text-lg font-semibold")
                ui.button(
                    icon="edit",
                    on_click=lambda: self.video_state.get_anchor_control_panel().open(),
                ).props("outline")

                with ui.grid(columns=4).classes("w-full gap-4"):
                    for anchor in anchors:
                        self._render_anchor_tile(anchor)

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
            .on("click", lambda a=anchor: self.on_play_anchor(a["t"]))
        ):
            with ui.column().classes("gap-2"):
                # ui.label(anchor["title"]).classes("font-medium")

                ui.label(self._format_time(anchor["t"])).classes("text-sm text-gray-500")

                with ui.row().classes("gap-1"):
                    for label in anchor.get("labels", []):
                        ui.badge(label).classes("bg-black text-white")

    @staticmethod
    def _format_time(seconds: int) -> str:
        m, s = divmod(int(seconds), 60)
        return f"{m}:{s:02d}"

from nicegui import ui

from ui.utils.utils import format_time

from .video_state import VideoState


# TODO: TimelineTab and MatadataTab have minor sync bugs when clips are present
class TimelineTab:

    def __init__(
        self,
        video_state: VideoState,
    ):
        self.video_state = video_state
        self.container = None
        self.scroll_area = None
        self.entries = {}
        self.video_state.add_refresh_callback(self.refresh)
        self.video_state.add_timeline_callback(self._refresh_active_anchor)

    def create_tab(self, container):
        self.container = container
        self.refresh()

    def refresh(self):
        if not self.container:
            return
        self.container.clear()
        with self.container:
            self.scroll_area = ui.scroll_area().classes("w-full h-full")
            with self.scroll_area:
                with ui.timeline(
                    side="right",
                    layout="dense",
                ).classes("w-full"):
                    self._render_entries()

    # TODO: reuse seek_anchor()
    def _play_anchor(self, anchor):

        anchor_id = self._anchor_id(anchor)

        self.video_state.current_playback_time = anchor["start"]

        self.video_state.set_active_anchor(anchor_id)
        self.video_state.set_active_metadata_row(anchor_id)

        ui.run_javascript(
            f"""
            if(window.seekYTPlayer){{
                window.seekYTPlayer({anchor['start']});
            }}
            """
        )

    def _anchor_id(self, anchor):
        return anchor.get("anchor_id") or anchor.get("id")

    def _render_entries(self):
        self.entries.clear()
        active_id = self.video_state.active_anchor_id

        anchors = sorted(
            self.video_state.anchor_draft,
            key=lambda a: a["start"],
        )
        for anchor in anchors:
            is_active = self._anchor_id(anchor) == active_id
            color = "primary" if is_active else "grey"
            icon = "play_arrow" if is_active else "bookmark"
            with ui.timeline_entry(
                title=format_time(anchor["start"]),
                color=color,
                icon=icon,
            ) as entry:
                self.entries[self._anchor_id(anchor)] = entry
                with ui.card().classes("w-full cursor-pointer") as card:
                    ui.label(anchor.get("description", ""))
                    # ui.button(icon="play_arrow", on_click=lambda a=anchor: self._play_anchor(a)).props("flat dense")
                card.on("click", lambda a=anchor: self._play_anchor(a))

    def _refresh_active_anchor(self):
        active_id = self.video_state.active_anchor_id
        for anchor_id, entry in self.entries.items():
            try:
                if anchor_id == active_id:
                    entry._props["color"] = "primary"
                    entry._props["icon"] = "play_arrow"
                else:
                    entry._props["color"] = "grey"
                    entry._props["icon"] = "bookmark"
                entry.update()
            except Exception:
                pass
        self._scroll_to_active_safe()

    def _scroll_to_active_safe(self):
        ui.timer(
            0.05,
            self._scroll_to_active,
            once=True,
        )

    async def _scroll_to_active(self):
        anchors = sorted(
            self.video_state.anchor_draft,
            key=lambda a: a["start"],
        )
        if not anchors:
            return
        active_index = next(
            (i for i, a in enumerate(anchors) if (self._anchor_id(a) == self.video_state.active_anchor_id)),
            None,
        )
        if active_index is None:
            return
        percent = active_index / max(1, len(anchors) - 1)
        self.scroll_area.scroll_to(
            percent=percent,
            duration=0.2,
        )

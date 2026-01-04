from nicegui import ui


class AnchorControlPanel:
    def __init__(self, video_state):
        self.video_state = video_state
        self.dialog = None
        self.container = None
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
        self.dialog = None

    def _render_header(self):
        with ui.grid(columns="auto 1fr 2fr auto").classes(
            "w-full text-xs uppercase text-primary border-b pb-2 mb-2 font-semibold"
        ):
            ui.label("Time")
            ui.label("Title")
            ui.label("Labels")
            ui.label("Actions")

    def _handle_label_key(self, anchor, e):
        if e.key == " ":
            value = anchor["_label_buffer"].strip()
            if value and value not in anchor["_labels"]:
                anchor["_labels"].append(value)
                self.video_state.mark_anchor_dirty()
            anchor["_label_buffer"] = ""
            self.video_state.refresh()

    def _update_label_buffer(self, anchor, value):
        anchor["_label_buffer"] = value

    def _remove_label(self, anchor, label):
        anchor["_labels"].remove(label)
        self.video_state.mark_anchor_dirty()

    def _render_label_editor(self, anchor):
        # Input buffer
        with (
            ui.input(
                value=anchor["_label_buffer"],
                placeholder="Add label",
                on_change=lambda e, a=anchor: self._update_label_buffer(a, e.value),
            )
            .props("dense outlined")
            .classes("min-w-[120px]")
        ):
            # Existing chips
            for label in anchor["_labels"]:
                ui.chip(
                    label,
                    removable=True,
                    on_value_change=lambda lab=label, a=anchor: self._remove_label(a, lab),
                ).classes("text-xs")

    def _validate_and_update_time(self, anchor, value):
        try:
            parts = [int(p) for p in value.split(":")]
            if len(parts) == 2:
                m, s = parts
                start = m * 60 + s
            elif len(parts) == 3:
                h, m, s = parts
                start = h * 3600 + m * 60 + s
            else:
                raise ValueError

            anchor["_time"] = self._format_time(start)
            anchor["start"] = start
            self.video_state.mark_anchor_dirty()

        except Exception:
            ui.notify("Invalid time format (mm:ss or hh:mm:ss)", type="warning")

    def _render_anchor_row(self, anchor):
        with ui.grid(columns="auto 1fr 2fr auto").classes("w-full items-center border-b py-1 gap-2"):

            ui.input(value=anchor["_time"]).on(
                "blur", lambda e, a=anchor: self._validate_and_update_time(a, e.value)
            ).props("dense outlined").classes("w-[72px]")

            ui.input(
                value=anchor.get("title", ""),
                on_change=lambda e, a=anchor: self._update_title(a, e.value),
            ).props("dense outlined").classes("w-full overflow-x-auto whitespace-nowrap")

            self._render_label_editor(anchor)

            ui.button(
                icon="delete",
                on_click=lambda a=anchor: self._delete_anchor(a),
            ).props("flat dense color=negative")

    def _render(self):
        ui.label("Anchor Control Panel").classes("text-lg font-semibold mb-4")

        rows = sorted(self.video_state.anchor_draft, key=lambda a: a["start"])

        for a in rows:
            a.setdefault("_time", self._format_time(a["start"]))
            a.setdefault("_labels", list(a.get("labels", [])))
            a.setdefault("_label_buffer", "")

        self._render_header()

        for anchor in rows:
            self._render_anchor_row(anchor)

        with ui.row().classes("justify-end gap-2 mt-6"):
            ui.button("Cancel", on_click=self.dialog.close)
            ui.button("Save", on_click=self._save_and_close).props("color=black")

    def _update_title(self, anchor, value):
        anchor["title"] = value
        self.video_state.mark_anchor_dirty()

    def _delete_anchor(self, anchor):
        self.video_state.anchor_draft.remove(anchor)
        self.video_state.mark_anchor_dirty()
        self.video_state.refresh()

    def _save_and_close(self):
        for anchor in self.video_state.anchor_draft:
            # ---- Parse time (mm:ss or hh:mm:ss) ----
            try:
                parts = [int(p) for p in anchor["_time"].split(":")]
                if len(parts) == 2:
                    m, s = parts
                    anchor["start"] = m * 60 + s
                elif len(parts) == 3:
                    h, m, s = parts
                    anchor["start"] = h * 3600 + m * 60 + s
                else:
                    raise ValueError
            except Exception:
                ui.notify(
                    f"Invalid time format: {anchor.get('_time')}",
                    type="warning",
                )
                return

            # ---- Labels ----
            anchor["labels"] = list(anchor.get("_labels", []))

            # ---- Cleanup ----
            anchor.pop("_time", None)
            anchor.pop("_labels", None)

        print("Saving anchors:\n", self.video_state.anchor_draft)
        self.video_state.save_anchors()
        ui.notify("Anchors saved", type="positive")

    def _format_time(self, t: int) -> str:
        h, rem = divmod(t, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

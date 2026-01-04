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

    # --------------------------------------------------
    # UI
    # --------------------------------------------------
    def _render(self):
        ui.label("Anchor Control Panel").classes("text-lg font-semibold mb-4")

        rows = sorted(self.video_state.anchor_draft, key=lambda a: a["start"])

        # initialize editable fields
        for a in rows:
            a.setdefault("_time", self._format_time(a["start"]))
            a.setdefault("_labels", list(a.get("labels", [])))

        # ---------- Header ----------
        with ui.grid(columns="120px 1fr 2fr 48px").classes(
            "w-full font-semibold text-xs uppercase text-primary border-b pb-2 mb-2"
        ):
            ui.label("Time")
            ui.label("Title")
            ui.label("Labels")
            ui.label("Actions")

        # ---------- Rows ----------
        for anchor in rows:
            self._render_row(anchor)

        # ---------- Footer ----------
        with ui.row().classes("justify-end gap-2 mt-6"):
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
        with ui.grid(columns="120px 1fr 2fr 48px").classes("w-full items-center border-b py-1"):
            # ---- Time ----
            ui.input(
                value=anchor["_time"],
                on_change=lambda e, a=anchor: self._update_time(a, e.value),
            ).props(
                "dense outlined"
            ).classes("w-full")

            # ---- Title ----
            ui.input(
                value=anchor.get("title", ""),
                on_change=lambda e, a=anchor: self._update_title(a, e.value),
            ).props("dense outlined").classes("w-full")

            # ---- Labels (chips) ----
            with (
                ui.input(
                    on_change=lambda e, a=anchor: self._update_labels(a, e.value),
                )
                .props("dense outlined")
                .classes("w-full")
            ):
                for op in anchor["_labels"]:
                    ui.chip(op, removable=True).classes("text-xs bg-primary")

            # ---- Delete ----
            ui.button(
                icon="delete",
                on_click=lambda a=anchor: self._delete_anchor(a),
            ).props("flat dense color=negative")

    # --------------------------------------------------
    # Mutations
    # --------------------------------------------------
    def _update_time(self, anchor, value):
        anchor["_time"] = value
        self.video_state.mark_anchor_dirty()

    def _update_title(self, anchor, value):
        anchor["title"] = value
        self.video_state.mark_anchor_dirty()

    def _update_labels(self, anchor, value):
        anchor["_labels"] = value
        self.video_state.mark_anchor_dirty()

    def _delete_anchor(self, anchor):
        self.video_state.anchor_draft.remove(anchor)
        self.video_state.mark_anchor_dirty()
        self.video_state.refresh()

    # --------------------------------------------------
    # Save
    # --------------------------------------------------
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

    # --------------------------------------------------
    # Utils
    # --------------------------------------------------
    def _format_time(self, t: int) -> str:
        h, rem = divmod(t, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

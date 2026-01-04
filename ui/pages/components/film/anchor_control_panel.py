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

        # Always render sorted
        rows = sorted(self.video_state.anchor_draft, key=lambda a: a["start"])

        columns = [
            {"name": "start", "label": "Time", "field": "start"},
            {"name": "title", "label": "Title", "field": "title"},
            {"name": "labels", "label": "Labels", "field": "labels"},
            {"name": "actions", "label": "", "field": "actions"},
        ]

        table = ui.table(
            rows=rows,
            columns=columns,
            row_key="id",
            column_defaults={
                "align": "left",
                "headerClasses": "uppercase text-primary text-xs",
            },
        ).classes("w-full")

        # --- Timestamp cell ---
        table.add_slot(
            "body-cell-t",
            """
            <q-td>
                <q-input dense outlined v-model="props.row._time" class="w-20" />
            </q-td>
            """,
        )

        # --- Title cell ---
        table.add_slot(
            "body-cell-title",
            """
            <q-td>
                <q-input dense outlined v-model="props.row.title" />
            </q-td>
            """,
        )

        # --- Labels cell ---
        table.add_slot(
            "body-cell-labels",
            """
            <q-td>
                <q-input dense outlined v-model="props.row._labels" />
            </q-td>
            """,
        )

        # --- Delete button ---
        table.add_slot(
            "body-cell-actions",
            """
            <q-td class="text-right">
                <q-btn
                    flat dense icon="delete"
                    @click="$emit('delete', props.row)"
                />
            </q-td>
            """,
        )

        # Initialize derived editable fields
        for anchor in rows:
            anchor["_time"] = self._format_time(anchor["start"])
            anchor["_labels"] = ", ".join(anchor.get("labels", []))

        # Handle delete
        table.on(
            "delete",
            lambda e: self._delete_anchor(e.args),
        )

        # Footer actions
        with ui.row().classes("justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=self.dialog.close)

            save_btn = ui.button(
                "Save",
                on_click=self._save_and_close,
            ).props("color=black")

            save_btn.bind_enabled_from(
                self.video_state,
                "is_anchor_dirty",
            )

    def _delete_anchor(self, anchor):
        self.video_state.anchor_draft.remove(anchor)
        self.video_state.mark_anchor_dirty()
        self.video_state.refresh()  # Trigger re-render via refresh callback

    def _format_time(self, t):
        m, s = divmod(t, 60)
        return f"{m}:{s:02d}"

    def _save_and_close(self):
        for anchor in self.video_state.anchor_draft:
            # Parse time
            try:
                m, s = anchor["_time"].split(":")
                anchor["start"] = int(m) * 60 + int(s)
            except Exception:
                ui.notify(
                    f"Invalid time format for anchor '{anchor.get('title', '')}'",
                    type="warning",
                )
                return

            # Parse labels
            anchor["labels"] = [_.strip() for _ in anchor.get("_labels", "").split(",") if _.strip()]

            # Cleanup transient fields
            anchor.pop("_time", None)
            anchor.pop("_labels", None)

        self.video_state.save_anchors()
        ui.notify("Anchors saved", type="positive")

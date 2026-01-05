from uuid import uuid4

from nicegui import events, ui


class AnchorControlPanel:
    def __init__(self, video_state):
        self.video_state = video_state
        self.dialog = None
        self.table = None
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

    def _render(self):
        ui.label("Anchor Control Panel").classes("text-lg font-semibold mb-2")

        # Ensure stable IDs and transient fields
        for anchor in self.video_state.anchor_draft:
            if "id" not in anchor:
                anchor["id"] = str(uuid4())
            anchor["_time"] = self._format_time(anchor.get("start", 0))
            anchor["_labels"] = ", ".join(anchor.get("labels", []))

        columns = [
            {"name": "time", "label": "Time", "field": "_time", "align": "left"},
            {"name": "title", "label": "Title", "field": "title"},
            {"name": "labels", "label": "Labels", "field": "_labels"},
            {"name": "actions", "label": "Actions", "field": "actions"},
        ]

        rows = sorted(self.video_state.anchor_draft, key=lambda a: a.get("start", 0))

        self.table = ui.table(
            columns=columns,
            rows=rows,
            row_key="id",
            column_defaults={"align": "left", "headerClasses": "uppercase text-primary text-xs"},
        ).classes("w-full")

        self.table.add_slot(
            "body",
            r"""
            <q-tr :props="props">

                <!-- time -->
                <q-td key="time" :props="props">
                    {{ props.row._time }}
                    <q-popup-edit
                        v-model="props.row._time"
                        v-slot="scope"
                        @update:model-value="() => $parent.$emit('edit', props.row)"
                    >
                        <q-input v-model="scope.value" dense autofocus
                            placeholder="m:ss"
                            @keyup.enter="scope.set" />
                    </q-popup-edit>
                </q-td>

                <!-- title -->
                <q-td key="title" :props="props">
                    {{ props.row.title }}
                    <q-popup-edit
                        v-model="props.row.title"
                        v-slot="scope"
                        @update:model-value="() => $parent.$emit('edit', props.row)"
                    >
                        <q-input v-model="scope.value" dense autofocus
                            @keyup.enter="scope.set" />
                    </q-popup-edit>
                </q-td>

                <!-- labels -->
                <q-td key="labels" :props="props">
                    {{ props.row._labels }}
                    <q-popup-edit
                        v-model="props.row._labels"
                        v-slot="scope"
                        @update:model-value="() => $parent.$emit('edit', props.row)"
                    >
                        <q-input v-model="scope.value" dense autofocus
                            placeholder="comma, separated"
                            @keyup.enter="scope.set" />
                    </q-popup-edit>
                </q-td>
                <!-- delete -->
                <q-td key="actions" auto-width>
                    {{ props.row.actions }}
                    <q-btn color="red" dense flat icon="delete"
                        @click="() => $parent.$emit('delete', props.row)" />
                </q-td>
            </q-tr>
            """,
        )

        def on_edit(e: events.GenericEventArguments):
            # row already mutated by popup-edit
            self.video_state.mark_anchor_dirty()

        def on_delete(e: events.GenericEventArguments):
            self.video_state.anchor_draft.remove(e.args)
            self.video_state.mark_anchor_dirty()
            self.table.update()

        self.table.on("edit", on_edit)
        self.table.on("delete", on_delete)

        # -------------------------
        # Footer
        # -------------------------
        with ui.row().classes("justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=self.dialog.close)
            save_btn = ui.button("Save", on_click=self._save_and_close).props("color=black")
            save_btn.bind_enabled_from(self.video_state, "is_anchor_dirty")

    # -------------------------
    # Delete
    # -------------------------
    def _delete_anchor(self, row):
        self.video_state.anchor_draft.remove(row)
        self.video_state.mark_anchor_dirty()
        self.video_state.refresh()

    # -------------------------
    # Save anchors
    # -------------------------
    def _save_and_close(self):
        for anchor in self.video_state.anchor_draft:
            # Parse time
            try:
                m, s = anchor["_time"].split(":")
                anchor["start"] = int(m) * 60 + int(s)
            except Exception:
                ui.notify(f"Invalid time format for anchor '{anchor.get('title', '')}'", type="warning")
                return

            # Parse labels
            anchor["labels"] = [x.strip() for x in anchor.get("_labels", "").split(",") if x.strip()]
            print(f"Parsed labels: {anchor['labels']}")
            # Clean transient fields
            anchor.pop("_time", None)
            anchor.pop("_labels", None)

        print(f"Saving anchors:\n{self.video_state.anchor_draft}")
        self.video_state.save_anchors()
        ui.notify("Anchors saved", type="positive")

    # -------------------------
    # Helpers
    # -------------------------
    def _format_time(self, t):
        m, s = divmod(t, 60)
        return f"{m}:{s:02d}"

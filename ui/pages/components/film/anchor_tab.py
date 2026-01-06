from uuid import uuid4

from nicegui import events, ui

from .video_state import VideoState


class AnchorTab:

    def __init__(self, video_state: VideoState):
        self.video_state = video_state
        self.container = None

        # Register for video state refresh notifications
        self.video_state.add_refresh_callback(self.refresh)

    def create_tab(self, container):
        """Create the metaforge tab UI"""
        self.container = container
        self.refresh()

    def refresh(self):
        """Refresh the metaforge tab with current video data"""
        if not self.container:
            return

        self.container.clear()
        with self.container:
            self._create_metaforge_ui()

    def _create_metaforge_ui(self):

        # Ensure stable IDs + transient fields
        for anchor in self.video_state.anchor_draft:
            anchor.setdefault("id", str(uuid4()))
            anchor.setdefault("_time", self._format_time(anchor.get("start", 0)))
            anchor.setdefault("_labels", ", ".join(anchor.get("labels", [])))

        # Sort IN PLACE
        self.video_state.anchor_draft.sort(key=lambda a: a.get("start", 0))

        columns = [
            {"name": "time", "label": "Time", "field": "_time"},
            {"name": "title", "label": "Title", "field": "title"},
            {"name": "labels", "label": "Labels", "field": "_labels"},
            {"name": "actions", "label": "", "field": "actions"},
        ]

        self.table = ui.table(
            columns=columns,
            rows=self.video_state.anchor_draft,
            row_key="id",
            column_defaults={"align": "left"},
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
                        <q-input
                            v-model="scope.value"
                            dense autofocus
                            placeholder="m:ss"
                            @keyup.enter="scope.set"
                        />
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
                        <q-input
                            v-model="scope.value"
                            dense autofocus
                            @keyup.enter="scope.set"
                        />
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
                        <q-input
                            v-model="scope.value"
                            dense autofocus
                            placeholder="comma, separated"
                            @keyup.enter="scope.set"
                        />
                    </q-popup-edit>
                </q-td>

                <!-- delete -->
                <q-td key="actions" auto-width>
                    <q-btn
                        color="red"
                        dense flat icon="delete"
                        @click="() => $parent.$emit('delete', props.row.id)"
                    />
                </q-td>

            </q-tr>
            """,
        )

        # 🔑 MERGE PAYLOAD BACK INTO SOURCE OF TRUTH
        def on_edit(e: events.GenericEventArguments):
            payload = dict(e.args)
            anchor_id = payload.pop("id")

            for anchor in self.video_state.anchor_draft:
                if anchor["id"] == anchor_id:
                    anchor.update(payload)
                    break

            self.video_state.mark_anchor_dirty()

        def on_delete(e: events.GenericEventArguments):
            anchor_id = e.args
            self.video_state.anchor_draft[:] = [a for a in self.video_state.anchor_draft if a["id"] != anchor_id]
            self.video_state.mark_anchor_dirty()
            self.table.update()

        self.table.on("edit", on_edit)
        self.table.on("delete", on_delete)

        with ui.row().classes("justify-end gap-2 mt-4"):
            ui.button("Clear", on_click=self._clear_unsaved)
            save_btn = ui.button("Save", on_click=self._save).props("color=black")
            save_btn.bind_enabled_from(self.video_state, "is_anchor_dirty")

    def _clear_unsaved(self):
        self.video_state.reload_anchors()
        self.refresh()
        ui.notify("Unsaved changes cleared", type="info")

    def _save(self):
        for anchor in self.video_state.anchor_draft:
            try:
                m, s = anchor["_time"].split(":")
                anchor["start"] = int(m) * 60 + int(s)
            except Exception:
                ui.notify(
                    f"Invalid time format for anchor '{anchor.get('title', '')}'",
                    type="warning",
                )
                return

            anchor["labels"] = [x.strip() for x in anchor.get("_labels", "").split(",") if x.strip()]

            anchor.pop("_time", None)
            anchor.pop("_labels", None)

        print("Saving anchors:")
        for a in self.video_state.anchor_draft:
            print(a)

        self.video_state.save_anchors()
        ui.notify("Anchors saved", type="positive")

    def _format_time(self, t: int) -> str:
        m, s = divmod(t, 60)
        return f"{m}:{s:02d}"

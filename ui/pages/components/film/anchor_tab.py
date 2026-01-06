from uuid import uuid4

from nicegui import events, ui
from utils.dialog_puns import caught_john_doe

from .video_state import VideoState


class AnchorTab:

    def __init__(self, video_state: VideoState, on_play_anchor):
        self.video_state = video_state
        self.container = None
        self.on_play_anchor = on_play_anchor

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
            anchor.setdefault("_expand", False)
            anchor.setdefault("description", anchor.get("description", ""))

        # Sort IN PLACE
        self.video_state.anchor_draft.sort(key=lambda a: a.get("start", 0))

        columns = [
            {"name": "play", "label": "", "field": "play"},
            {"name": "time", "label": "Time", "field": "_time"},
            {"name": "title", "label": "Title", "field": "title"},
            {"name": "labels", "label": "Labels", "field": "_labels"},
            {"name": "expand", "label": "", "field": "expand"},
            {"name": "delete", "label": "", "field": "delete"},
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
            <!-- MAIN ROW -->
            <q-tr :props="props">

                <!-- play -->
                <q-td auto-width>
                    <q-btn
                        color="green"
                        dense flat icon="play_arrow"
                        @click="() => $parent.$emit('play', props.row.id)"
                    />
                </q-td>

                <!-- time -->
                <q-td>
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
                <q-td>
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
                <q-td>
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

                <!-- expand -->
                <q-td auto-width>
                    <q-btn
                        size="sm"
                        dense round flat
                        color="primary"
                        :icon="props.row._expand ? 'expand_less' : 'expand_more'"
                        @click="props.row._expand = !props.row._expand"
                    />
                </q-td>

                <!-- delete -->
                <q-td auto-width>
                    <q-btn
                        color="red"
                        dense flat icon="delete"
                        @click="() => $parent.$emit('delete', props.row.id)"
                    />
                </q-td>

            </q-tr>

            <!-- EXPANDED ROW -->
            <q-tr v-show="props.row._expand">
                <q-td colspan="100%">
                    <div class="q-pa-sm">

                        <q-input
                            v-model="props.row.description"
                            type="textarea"
                            dense
                            autogrow
                            placeholder="Add description for this anchor..."
                            @blur="$parent.$emit('edit', props.row)"
                        />

                    </div>
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

        def on_play(e: events.GenericEventArguments):
            anchor_id = e.args
            for anchor in self.video_state.anchor_draft:
                if anchor["id"] == anchor_id:
                    self.on_play_anchor(anchor["start"])
                    break

        self.table.on("edit", on_edit)
        self.table.on("play", on_play)
        self.table.on("delete", on_delete)

        with ui.row().classes("justify-end gap-2 mt-4"):
            ui.button("Clear", on_click=self._clear_unsaved)
            save_btn = ui.button("Save", on_click=caught_john_doe if not self.video_state.user else self._save).props(
                "color=black"
            )
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

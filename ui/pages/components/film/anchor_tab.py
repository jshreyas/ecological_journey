import re
from uuid import uuid4

from nicegui import events, ui
from utils.dialog_puns import caught_john_doe

from .video_state import VideoState

LABEL_REGEX = re.compile(r"#([^\s#]+)")
PARTNER_REGEX = re.compile(r"@([^\s#]+)")


class AnchorTab:

    def __init__(self, video_state: VideoState, on_play_anchor):
        self.video_state = video_state
        self.container = None
        self.on_play_anchor = on_play_anchor

        self.video_state.add_refresh_callback(self.refresh)

    def create_tab(self, container):
        self.container = container
        self.refresh()

    def refresh(self):
        if not self.container:
            return
        self.container.clear()
        with self.container:
            self._create_metaforge_ui()

    def _create_metaforge_ui(self):

        # ---------- normalize anchors ----------
        for anchor in self.video_state.anchor_draft:
            anchor.setdefault("id", str(uuid4()))
            anchor.setdefault("_time", self._format_time(anchor.get("start", 0)))
            anchor.setdefault("description", anchor.get("description", ""))

            anchor.setdefault("_expand", False)
            anchor.setdefault("_dirty", False)

        self.video_state.anchor_draft.sort(key=lambda a: a.get("start", 0))

        # ---------- table ----------
        columns = [
            {"name": "play", "label": "", "field": "play"},
            {"name": "time", "label": "Time", "field": "_time"},
            {"name": "description", "label": "Notes", "field": "description"},
            {"name": "delete", "label": "", "field": "delete"},
        ]

        # build rows: first row is the video description (single-column),
        # followed by the anchor draft rows
        video_row = {
            "id": "__video_description__",
            "_is_video_description": True,
            "description": self.video_state.video_description_draft or "",
            "_dirty": self.video_state.is_video_description_dirty,
        }
        combined_rows = [video_row] + list(self.video_state.anchor_draft)

        self.table = (
            ui.table(
                columns=columns,
                rows=combined_rows,
                row_key="id",
                column_defaults={"align": "left"},
            )
            .props("hide-header")
            .classes("w-full")
        )

        self.table.add_slot(
            "body",
            r"""
            <!-- VIDEO DESCRIPTION ROW (single-column first row) -->
            <q-tr v-if="props.row && props.row._is_video_description" :props="props" :class="props.row._dirty ? 'text-primary' : ''">
            <q-td colspan="100%" class="q-pa-sm">

                <!-- rendered description -->
                <div
                style="
                        max-height: 120px;
                        overflow-y: auto;
                        white-space: pre-wrap;
                        line-height: 1.6;
                        cursor: pointer;
                "
                >
                <template
                    v-for="(part, idx) in (props.row.description || '').split(/(#[^\s#@]+|@[^\s#@]+)/g)"
                        :key="idx"
                >
                        <q-chip
                        v-if="part.startsWith('#')"
                        dense
                        size="sm"
                        outline
                        color="primary"
                        icon="label"
                        class="q-mr-xs"
                        >
                        {{ part.slice(1) }}
                        </q-chip>

                        <q-chip
                        v-else-if="part.startsWith('@')"
                        dense
                        outline
                        size="sm"
                        icon="person"
                        color="primary"
                        class="q-mr-xs"
                        >
                        {{ part.slice(1) }}
                        </q-chip>

                        <span v-else>{{ part }}</span>
                </template>

                <span v-if="!props.row.description" class="text-grey">
                        Click to add video description, #labels, @partners…
                </span>
                </div>

                <!-- editor -->
                <q-popup-edit
                v-slot="scope"
                @update:model-value="(val) => $parent.$emit('edit-video-description', val)"
                v-model="props.row.description"
                >
                <div class="row q-gutter-sm">
                    <div class="col">
                    <q-input
                        v-model="scope.value"
                        type="textarea"
                        dense
                        autogrow
                        autofocus
                        placeholder="Video-level notes. Supports #labels and @partners"
                    />
                    </div>
                    <div class="col-auto justify-end">
                    <q-btn
                        dense
                        flat
                        color="primary"
                        icon="send"
                        @click="scope.set"
                    />
                    </div>
                </div>
                </q-popup-edit>

                </q-td>
                </q-tr>

                <!-- MAIN ROW -->
                <q-tr v-else :props="props" :class="props.row._dirty ? 'text-primary' : ''">

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
                        <!-- DESCRIPTION (inline chips replacing #labels and @partners) -->
                        <q-td>

                        <!-- inline rendered description -->
                        <div style="white-space: pre-wrap; line-height: 1.6;">
                                <template
                                v-for="(part, idx) in props.row.description.split(/(#[^\s#@]+|@[^\s#@]+)/g)"
                                :key="idx"
                                >
                                <!-- LABEL CHIP -->
                                <q-chip
                                        v-if="part.startsWith('#')"
                                        dense
                                        size="sm"
                                        outline
                                        color="primary"
                                        icon="label"
                                        class="q-mr-xs"
                                >
                                        {{ part.slice(1) }}
                                </q-chip>

                                <!-- PARTNER CHIP -->
                                <q-chip
                                        v-else-if="part.startsWith('@')"
                                        dense
                                        outline
                                        size="sm"
                                        icon="person"
                                        color="primary"
                                        class="q-mr-xs"
                                >
                                        {{ part.slice(1) }}
                                </q-chip>

                                <!-- normal text -->
                                <span v-else>
                                        {{ part }}
                                </span>
                                </template>
                        </div>

                        <!-- editor -->
                        <q-popup-edit
                                v-model="props.row.description"
                                v-slot="scope"
                                @update:model-value="() => $parent.$emit('edit', props.row)"
                        >
                                <div class="row q-gutter-sm">
                                <div class="col">
                                    <q-input
                                    v-model="scope.value"
                                    type="textarea"
                                    dense
                                    autogrow
                                    autofocus
                                    placeholder="use #labels and @partners inline"
                                    />
                                </div>
                                <div class="col-auto justify-end">
                                    <q-btn
                                    dense
                                    flat
                                    color="primary"
                                    icon="send"
                                    @click="scope.set"
                                    />
                                </div>
                                </div>
                        </q-popup-edit>
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
                """,
        )

        # ---------- handlers ----------
        def on_edit(e: events.GenericEventArguments):
            payload = dict(e.args)
            anchor_id = payload.pop("id")

            for anchor in self.video_state.anchor_draft:
                if anchor["id"] == anchor_id:
                    anchor.update(payload)
                    anchor["_dirty"] = True
                    break

            self.video_state.mark_anchor_dirty()
            self.refresh()

        def on_delete(e: events.GenericEventArguments):
            anchor_id = e.args
            self.video_state.anchor_draft[:] = [a for a in self.video_state.anchor_draft if a["id"] != anchor_id]
            self.video_state.mark_anchor_dirty()
            self.refresh()

        def on_play(e: events.GenericEventArguments):
            anchor_id = e.args
            for anchor in self.video_state.anchor_draft:
                if anchor["id"] == anchor_id:
                    self.on_play_anchor(anchor["start"])
                    break

        def on_edit_video_description(e: events.GenericEventArguments):
            value = e.args

            # 1️⃣ update centralized state
            self.video_state.video_description_draft = value
            self.video_state.is_video_description_dirty = True

            # 2️⃣ update synthetic row immediately
            for row in self.table.rows:
                if row.get("_is_video_description"):
                    row["description"] = value
                    row["_dirty"] = True
                    break

            self.video_state.mark_anchor_dirty()

            ui.notify(self.video_state.video_description_draft, type="info")

            # optional but safe
            self.refresh()

        self.table.on("edit", on_edit)
        self.table.on("play", on_play)
        self.table.on("delete", on_delete)
        self.table.on("edit-video-description", on_edit_video_description)

        # ---------- footer ----------
        with ui.row().classes("justify-end gap-2 mt-4"):
            ui.button("Clear", on_click=self._clear_unsaved)
            save_btn = ui.button(
                "Save",
                on_click=caught_john_doe if not self.video_state.user else self._save,
            ).props("color=black")
            save_btn.bind_enabled_from(self.video_state, "is_anchor_dirty")

    def _clear_unsaved(self):
        self.video_state.reload_anchors()
        self.refresh()
        ui.notify("Unsaved changes cleared", type="info")

    def _save(self):
        # TODO: combine video descirption and anchors save into single API call
        for anchor in self.video_state.anchor_draft:

            # time
            try:
                m, s = anchor["_time"].split(":")
                anchor["start"] = int(m) * 60 + int(s)
            except Exception:
                ui.notify(
                    f"Invalid time format for anchor '{anchor.get('_time', '')}'",
                    type="warning",
                )
                return

            # extract labels from description
            desc = anchor.get("description", "")
            anchor["labels"] = list(set(LABEL_REGEX.findall(desc)))
            anchor["partners"] = list(set(PARTNER_REGEX.findall(desc)))

            anchor.pop("_time", None)
            anchor.pop("_dirty", None)

        self.video_state.save_anchors()

        if self.video_state.is_video_description_dirty:
            self.video_state.is_video_description_dirty = False
            video_metadata = {}
            # extract labels from description
            video_desc = self.video_state.video_description_draft
            video_metadata["notes"] = video_desc
            video_metadata["labels"] = list(set(LABEL_REGEX.findall(video_desc)))
            video_metadata["partners"] = list(set(PARTNER_REGEX.findall(video_desc)))

            self.video_state.save_video_description(video_metadata)

            # rebuild UI so description row shows saved state
            self.refresh()

        for anchor in self.video_state.anchor_draft:
            anchor["_dirty"] = False

        ui.notify("Film metadata saved", type="positive")

    def _format_time(self, t: int) -> str:
        m, s = divmod(t, 60)
        return f"{m}:{s:02d}"

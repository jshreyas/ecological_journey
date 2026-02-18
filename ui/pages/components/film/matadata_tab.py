import re
from uuid import uuid4

from nicegui import events, ui

from ui.utils.dialog_puns import caught_john_doe
from ui.utils.utils import format_time

from .video_state import VideoState

LABEL_REGEX = re.compile(r"#([^\s#]+)")
PARTNER_REGEX = re.compile(r"@([^\s#]+)")


# TODO: Clip creation? or Anchor to Clip?
class MatadataTab:

    def __init__(
        self,
        video_state: VideoState,
        on_play_anchor,
        on_play_clip=None,
        on_share_clip=None,
    ):

        self.video_state = video_state
        self.container = None
        self.on_play_anchor = on_play_anchor
        self.on_play_clip = on_play_clip
        self.on_share_clip = on_share_clip

        self.video_state.add_refresh_callback(self.refresh)

    def create_tab(self, container):
        self.container = container
        self.refresh()

    def refresh(self):
        if not self.container:
            return
        self.container.clear()
        with self.container:
            self._create_metadata_ui()

    def _create_metadata_ui(self):

        video_row = {
            "id": "__video_description__",
            "_is_video_description": True,
            "description": self.video_state.video_description_draft or "",
            "_dirty": self.video_state.video_description_dirty,
        }
        anchor_rows = []
        clip_rows = []
        for anchor in self.video_state.anchor_draft:
            anchor.setdefault("id", str(uuid4()))
            anchor.setdefault("_time", format_time(anchor.get("start", 0)))
            anchor.setdefault("description", anchor.get("description", ""))
            anchor.setdefault("_dirty", False)
            anchor.setdefault("_type", "anchor")
            anchor_rows.append(anchor)

        self.video_state.anchor_draft.sort(key=lambda a: a.get("start", 0))

        for clip in self.video_state.clip_draft:
            clip.setdefault("id", str(uuid4()))
            clip.setdefault("_time", format_time(clip.get("start", 0)))
            clip.setdefault("_end_time", format_time(clip.get("end", 0)))
            clip.setdefault("_type", "clip")
            clip.setdefault("_dirty", False)

            description = (clip.get("description") or "").strip()
            labels = clip.get("labels", []) or []
            partners = clip.get("partners", []) or []

            # Only append missing tags
            missing_labels = [lab for lab in labels if f"#{lab}" not in description]

            missing_partners = [par for par in partners if f"@{par}" not in description]

            if missing_labels or missing_partners:
                append_text = " ".join([f"#{lab}" for lab in missing_labels] + [f"@{par}" for par in missing_partners])

                if description:
                    description = f"{description}\n{append_text}"
                else:
                    description = append_text

            clip.setdefault("description", description)
            clip_rows.append(clip)

        # Ensure drafts are sorted internally (no regression)
        self.video_state.anchor_draft.sort(key=lambda a: a.get("start", 0))
        self.video_state.clip_draft.sort(key=lambda c: c.get("start", 0))

        # Combine anchors + clips
        time_rows = anchor_rows + clip_rows

        # Sort unified by numeric start time
        time_rows.sort(key=lambda r: r.get("start", 0))

        combined_rows = [video_row] + time_rows
        columns = [
            {"name": "play", "label": "", "field": "play"},
            {"name": "timestamp", "label": "Timestamp", "field": "timestamp"},
            {"name": "description", "label": "Notes", "field": "description"},
            {"name": "actions", "label": "", "field": "actions"},
        ]
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
                        Click to add notes, #labels, @partners…
                </span>
                </div>

                <!-- editor -->
                <q-popup-edit
                v-slot="scope"
                @update:model-value="(val) => $parent.$emit('edit-video-description', val)"
                v-model="props.row.description"
                >
                <q-input
                    v-model="scope.value"
                    type="textarea"
                    dense
                    autogrow
                    autofocus
                    placeholder="Add notes. Supports #labels and @partners"
                    @keydown.enter.exact.prevent="scope.set"
                    @keydown.command.enter.prevent="() => {
                        scope.value += '\n'
                    }"
                />
                </q-popup-edit>

                </q-td>
                </q-tr>

                <!-- MAIN ROW -->
                <q-tr
                v-else
                :props="props"
                :class="props.row._dirty ? 'text-primary' : ''"
                >

                <!-- PLAY -->
                <q-td auto-width>
                    <q-btn
                    dense flat icon="play_arrow"
                    color="green"
                    @click="() => $parent.$emit('play', props.row)"
                    />
                </q-td>

                <!-- TIMESTAMP COLUMN -->
                <q-td>

                    <!-- ANCHOR -->

                    <div v-if="props.row._type === 'anchor'" class="column">

                    <!-- START -->
                    <div>
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
                    </div>

                    <!-- subtle add-end line -->
                    <div
                        class="q-mt-xs"
                        style="
                        height: 2px;
                        background: rgba(0,0,0,0.15);
                        cursor: pointer;
                        transition: background 0.2s ease;
                        "
                        @mouseenter="$event.target.style.background='rgba(128,0,128,0.5)'"
                        @mouseleave="$event.target.style.background='rgba(0,0,0,0.15)'"
                        @click="() => $parent.$emit('toggle-clip', props.row)"
                    ></div>

                    </div>


                    <!-- CLIP -->
                    <div v-else class="column">

                    <!-- START -->
                    <div>
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
                    </div>

                    <!-- subtle remove-end line -->
                    <div
                        class="q-mt-xs"
                        style="
                        height: 2px;
                        background: rgba(128,0,128,0.3);
                        cursor: pointer;
                        transition: background 0.2s ease;
                        "
                        @mouseenter="$event.target.style.background='rgba(128,0,128,0.8)'"
                        @mouseleave="$event.target.style.background='rgba(128,0,128,0.3)'"
                        @click="() => $parent.$emit('toggle-clip', props.row)"
                    ></div>

                    <!-- END -->
                    <div class="q-mt-xs">
                        {{ props.row._end_time }}
                        <q-popup-edit
                        v-model="props.row._end_time"
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
                    </div>

                    </div>

                </q-td>

                <!-- DESCRIPTION -->
                <q-td>

                    <div style="white-space: pre-wrap; line-height: 1.6;">
                    <template
                        v-for="(part, idx) in props.row.description.split(/(#[^\s#@]+|@[^\s#@]+)/g)"
                        :key="idx"
                    >
                        <q-chip
                        v-if="part.startsWith('#')"
                        dense size="sm" outline
                        color="primary"
                        icon="label"
                        class="q-mr-xs"
                        >
                        {{ part.slice(1) }}
                        </q-chip>

                        <q-chip
                        v-else-if="part.startsWith('@')"
                        dense size="sm" outline
                        color="primary"
                        icon="person"
                        class="q-mr-xs"
                        >
                        {{ part.slice(1) }}
                        </q-chip>

                        <span v-else>{{ part }}</span>
                    </template>
                    </div>

                    <q-popup-edit
                    v-model="props.row.description"
                    v-slot="scope"
                    @update:model-value="() => $parent.$emit('edit', props.row)"
                    >
                    <q-input
                        v-model="scope.value"
                        type="textarea"
                        dense
                        autogrow
                        autofocus
                        placeholder="use #labels and @partners"
                        @keydown.enter.exact.prevent="scope.set"
                        @keydown.command.enter.prevent="() => {
                            scope.value += '\n'
                        }"
                    />
                    </q-popup-edit>
                </q-td>

                <!-- ACTIONS -->
                <q-td auto-width>

                    <!-- SHARE -->
                    <q-btn
                    dense flat icon="share"
                    color="accent"
                    @click="() => $parent.$emit('share', props.row)"
                    />

                    <!-- DELETE -->
                    <q-btn
                    dense flat icon="delete"
                    color="red"
                    @click="() => $parent.$emit('delete', props.row)"
                    />

                </q-td>

                </q-tr>

                """,
        )

        # ---------- handlers ----------
        def on_edit(e: events.GenericEventArguments):
            # TODO: on editing timestamps for clips and anchors, playing it before saving and after editing timestamps are not honored
            row = dict(e.args)
            row_id = row["id"]

            # Mark dirty
            for r in self.table.rows:
                if r["id"] == row_id:
                    r.update(row)
                    r["_dirty"] = True
                    break

            self.video_state.mark_metadata_dirty()
            self.refresh()

        def on_delete(e: events.GenericEventArguments):
            row = e.args
            if row["_type"] == "clip":
                self.video_state.clip_draft[:] = [c for c in self.video_state.clip_draft if c.get("id") != row["id"]]
            else:
                self.video_state.anchor_draft[:] = [
                    a for a in self.video_state.anchor_draft if a.get("id") != row["id"]
                ]
            self.video_state.mark_metadata_dirty()
            self.refresh()

        def on_play(e: events.GenericEventArguments):
            row = e.args
            if row["_type"] == "anchor":
                self.on_play_anchor(row["start"])
            else:
                if self.on_play_clip:
                    self.on_play_clip(row)

        def on_share(e: events.GenericEventArguments):
            row = e.args
            if row["_type"] == "clip":
                if self.on_share_clip:
                    self.on_share_clip(row)
            else:
                ui.notify("Share for anchor clicked (stub)", type="info")

        def on_edit_video_description(e: events.GenericEventArguments):
            value = e.args

            self.video_state.video_description_draft = value
            self.video_state.video_description_dirty = True
            self.video_state._metadata_dirty = True
            self.refresh()

        async def on_toggle_clip(e: events.GenericEventArguments):
            row = e.args

            # ---------- ANCHOR → CLIP ----------
            if row["_type"] == "anchor":
                current_time = await ui.run_javascript("window.getYTCurrentTime();")
                if current_time is None:
                    ui.notify("Player not ready", type="warning")
                    return

                try:
                    self.video_state.convert_anchor_to_clip(
                        anchor_id=row["id"],
                        end_time=int(current_time),
                    )
                    ui.notify("Converted to clip", type="positive")
                except ValueError as err:
                    ui.notify(str(err), type="warning")

            # ---------- CLIP → ANCHOR ----------
            else:
                self.video_state.convert_clip_to_anchor(row["id"])
                ui.notify("Converted to anchor", type="info")

        self.table.on("edit", on_edit)
        self.table.on("play", on_play)
        self.table.on("share", on_share)
        self.table.on("delete", on_delete)
        self.table.on("edit-video-description", on_edit_video_description)
        self.table.on("toggle-clip", on_toggle_clip)

        # ---------- footer ----------
        with ui.row().classes("justify-end gap-2 mt-4"):
            ui.button("Clear", on_click=self._clear_unsaved)
            save_btn = ui.button(
                "Save",
                on_click=caught_john_doe if not self.video_state.user else self._save,
            ).props("color=black")
            save_btn.bind_enabled_from(self.video_state, "_metadata_dirty")

    def _clear_unsaved(self):
        self.video_state.reload_metadata()
        self.refresh()
        ui.notify("Unsaved changes cleared", type="info")

    def _save(self):
        # TODO: check if dirty flags are true, only then call save_video_metadata()
        try:
            self.video_state.save_video_metadata()
        except ValueError as e:
            ui.notify(str(e), type="warning")
            return

        ui.notify("Film metadata saved", type="positive")

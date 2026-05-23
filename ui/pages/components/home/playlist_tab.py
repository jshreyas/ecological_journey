import asyncio

from nicegui import ui

from ui.data.crud import AuthError
from ui.log import log
from ui.utils.dialog_puns import caught_john_doe
from ui.utils.youtube import fetch_playlist_items, fetch_playlist_metadata

from .state import State

SYNC_OK = "ok"
SYNC_NOOP = "noop"
SYNC_RETRY_SOON = "retry_soon"
SYNC_ERROR = "error"


class PlaylistTab:
    """Component for displaying playlist tab"""

    def __init__(self, home_state: State):
        self.home_state = home_state
        self.container = None

        self.home_state.add_refresh_callback(self.refresh)

    def create_tab(self, container):
        """Create the playlist tab UI"""
        self.container = container
        self.refresh()

    def refresh(self):
        """Refresh the playlist tab with current video data"""
        if not self.container:
            return

        self.container.clear()
        with self.container:
            self._create_playlist_ui()

    def _create_playlist_ui(self):
        """Create the playlist UI"""

        def render_add_playlist_card():
            with ui.card().classes("w-full p-4 border border-gray-300 rounded-lg bg-white shadow-md gap-3"):
                ui.label("➕ Playlist by ID").classes("text-md font-bold")
                playlist_verified = {"status": False}
                playlist_id_input = ui.input("YouTube Playlist ID").classes("w-full text-sm")

                async def verify_playlist():
                    playlist_id = playlist_id_input.value.strip()
                    if not playlist_id:
                        ui.notify("❌ Please enter a Playlist ID.", type="warning")
                        fetch_button.disable()
                        playlist_verified["status"] = False
                        return
                    metadata = await fetch_playlist_metadata(playlist_id)
                    if metadata and "title" in metadata:
                        ui.notify(f'✅ Playlist verified: {metadata["title"]}', type="success")
                        fetch_button.enable()
                        playlist_verified["status"] = True
                    else:
                        ui.notify("❌ Invalid Playlist ID or playlist not found.", type="error")
                        fetch_button.disable()
                        playlist_verified["status"] = False

                def on_input_change():
                    fetch_button.disable()
                    playlist_verified["status"] = False

                async def fetch_playlist_videos():
                    if not playlist_verified["status"]:
                        ui.notify("❌ Please verify the playlist first.", type="warning")
                        return
                    playlist_id = playlist_id_input.value.strip()
                    metadata = await fetch_playlist_metadata(playlist_id)
                    playlist_name = metadata.get("title", playlist_id)
                    ui.notify(f"Fetching videos for playlist: {playlist_name}")
                    spinner = ui.spinner(size="lg").props("color=primary")
                    ui.timer(0.1, lambda: spinner.set_visibility(True), once=True)

                    async def task():
                        playlist = self.home_state.create_playlist(
                            playlist_name,
                            playlist_id,
                        )
                        result = await self.sync_playlist(playlist)
                        spinner.set_visibility(False)
                        if result == SYNC_OK:
                            ui.notify("✅ Playlist created and synced")
                        elif result == SYNC_NOOP:
                            ui.notify("ℹ️ Playlist added (no videos yet)")
                        else:
                            ui.notify("⚠️ Playlist added, sync failed")

                        playlist_id_input.value = ""
                        fetch_button.disable()
                        playlist_verified["status"] = False

                    ui.timer(0.2, task, once=True)

                playlist_id_input.on("change", on_input_change)
                with ui.row().classes("w-full justify-start gap-4"):
                    ui.button(
                        on_click=(caught_john_doe if not self.home_state.user else verify_playlist),
                        icon="check_circle",
                    ).props("flat round").tooltip("Verify Playlist")
                    fetch_button = ui.button(icon="download").props("flat round").tooltip("Fetch Videos")
                    fetch_button.disable()
                    fetch_button.on("click", fetch_playlist_videos)

        with self.container:
            if not self.home_state.user:
                all_playlists = self.home_state.load_playlists()
                owned_ids = set()
                rows = self._build_playlist_rows(
                    playlists=all_playlists,
                    logged_in=False,
                )
            else:
                both = self.home_state.load_playlists_for_user()
                owned = both["owned"]
                member = both["member"]
                owned_ids = {pl["_id"] for pl in owned}
                all_playlists = owned + [p for p in member if p["_id"] not in owned_ids]
                rows = self._build_playlist_rows(
                    playlists=all_playlists,
                    owned_ids=owned_ids,
                    logged_in=True,
                )

            columns = [
                {
                    "name": "name",
                    "label": "Playlist",
                    "field": "name",
                    "align": "left",
                    "sortable": True,
                },
                {
                    "name": "video_count",
                    "label": "Videos",
                    "field": "video_count",
                    "align": "left",
                    "sortable": True,
                },
                {
                    "name": "actions",
                    "label": "",
                    "field": "actions",
                    "align": "center",
                },
            ]

            if not self.home_state.user:
                columns[-1]["classes"] = "hidden"
                columns[-1]["headerClasses"] = "hidden"

            playlist_table = (
                ui.table(
                    columns=columns,
                    rows=rows,
                    row_key="_id",
                    pagination=20,
                )
                .classes("w-full")
                .props("hide-header")
            )

            playlist_table.add_slot(
                "body-cell-name",
                r"""
                <q-td key="name" :props="props">
                    <div class="row no-wrap items-stretch full-width">
                        <div
                            :style="{
                                width: '6px',
                                backgroundColor: props.row.color,
                                borderRadius: '4px',
                                marginRight: '10px',
                                marginLeft: '0px',
                            }"
                        ></div>
                        <div class="font-medium">
                            {{ props.row.name }}
                        </div>
                    </div>
                </q-td>
                """,
            )

            playlist_table.add_slot(
                "body-cell-video_count",
                r"""
                <q-td key="video_count" :props="props">

                    🎬 {{ props.row.video_count }}

                </q-td>
                """,
            )

            playlist_table.add_slot(
                "body-cell-actions",
                r"""
                <q-td key="actions" :props="props">

                    <div class="row justify-center items-center q-gutter-sm">

                        <!-- Sync -->
                        <q-spinner
                            v-if="props.row.syncing"
                            color="primary"
                            size="20px"
                        />

                        <q-btn
                            v-else
                            icon="sync"
                            flat
                            round
                            dense
                            color="primary"
                            :disable="!props.row.can_sync"
                            @click="$parent.$emit('sync_playlist', props.row)"
                        />

                        <!-- Color Picker -->
                        <q-btn
                            icon="palette"
                            color="primary"
                            flat
                            round
                            dense
                        >

                            <q-popup-proxy
                                ref="popup"
                                cover
                                transition-show="scale"
                                transition-hide="scale"
                                @before-show="
                                    props.row.temp_color = props.row.color
                                "
                            >

                                <div class="q-pa-md">

                                    <q-form
                                        class="q-gutter-md"
                                        @submit.prevent="

                                            props.row.color = props.row.temp_color;

                                            $parent.$emit(
                                                'update_playlist_color',
                                                {
                                                    row: props.row,
                                                    color: props.row.temp_color
                                                }
                                            );

                                            $refs.popup.hide();
                                        "
                                    >

                                        <q-color
                                            v-model="props.row.temp_color"
                                        />

                                        <div class="row justify-end">
                                            <q-btn
                                                icon="send"
                                                type="submit"
                                                color="primary"
                                                flat
                                                round
                                            />
                                        </div>

                                    </q-form>

                                </div>

                            </q-popup-proxy>

                        </q-btn>

                    </div>

                </q-td>
                """,
            )

            async def handle_sync(e):

                row = e.args

                playlist_obj = next(
                    (p for p in all_playlists if p["_id"] == row["_id"]),
                    None,
                )

                if not playlist_obj:
                    ui.notify(
                        "Playlist not found",
                        type="negative",
                    )
                    return

                # anonymous users
                if not self.home_state.user:
                    caught_john_doe()
                    return

                # members cannot sync
                if playlist_obj["_id"] not in owned_ids:
                    ui.notify(
                        "Only playlist owners can sync",
                        type="warning",
                    )
                    return

                self._trigger_playlist_sync(playlist_obj, row)

            async def handle_color_update(e):

                row = e.args["row"]
                color = e.args["color"]

                playlist_obj = next(
                    (p for p in all_playlists if p["_id"] == row["_id"]),
                    None,
                )
                if not playlist_obj:
                    ui.notify(
                        "Playlist not found",
                        type="negative",
                    )
                    return

                if playlist_obj["_id"] not in owned_ids:
                    ui.notify(
                        "Only playlist owners can change colors",
                        type="warning",
                    )
                    return
                old_color = row["color"]
                try:
                    row["color"] = color
                    playlist_table.update()
                    self.home_state.update_playlist_color(
                        playlist_obj["_id"],
                        color,
                    )
                    playlist_obj["color"] = color
                except Exception as ex:
                    row["color"] = old_color
                    playlist_table.update()
                    ui.notify(
                        f"Failed to update color: {str(ex)}",
                        type="negative",
                    )

            playlist_table.on(
                "sync_playlist",
                handle_sync,
            )
            playlist_table.on(
                "update_playlist_color",
                handle_color_update,
            )

            render_add_playlist_card()

    def _trigger_playlist_sync(self, playlist_obj: dict, row: dict):

        row["syncing"] = True
        self.container.update()

        async def do_sync():

            try:

                result = await self.sync_playlist(playlist_obj)
                with self.container:
                    if result == SYNC_OK:
                        ui.notify(
                            "Playlist synced successfully",
                            type="positive",
                        )

                    elif result == SYNC_NOOP:
                        ui.notify(
                            "No new videos to sync",
                            type="info",
                        )

                    elif result == SYNC_RETRY_SOON:
                        ui.notify(
                            "Upload still in progress — try again shortly",
                            type="warning",
                        )

                    else:
                        ui.notify(
                            "Sync failed",
                            type="negative",
                        )

            except Exception as e:
                with self.container:
                    ui.notify(
                        f"❌ Sync failed: {str(e)}",
                        type="negative",
                    )

            finally:
                row["syncing"] = False
                self.container.update()

        asyncio.create_task(do_sync())

    def _build_playlist_rows(
        self,
        playlists,
        owned_ids=None,
        logged_in=False,
    ):
        owned_ids = owned_ids or set()
        rows = []
        for playlist in playlists:
            is_owned = playlist["_id"] in owned_ids
            rows.append(
                {
                    "_id": playlist["_id"],
                    "name": playlist["name"],
                    "video_count": playlist.get("video_count", 0),
                    "color": playlist.get("color"),
                    "can_sync": is_owned if logged_in else True,
                    "is_owned": is_owned,
                    "temp_color": None,
                    "syncing": False,
                    "show_color_picker": False,
                }
            )
        return rows

    async def sync_playlist(self, playlist_obj: dict) -> str:
        playlist_name = playlist_obj["name"]
        try:
            existing_videos = self.home_state.load_videos_by_playlist(playlist_obj["_id"])

            if existing_videos:
                latest_saved_date = max(video["date"] for video in existing_videos)
                existing_video_ids = [video["video_id"] for video in existing_videos]
            else:
                latest_saved_date = None
                existing_video_ids = set()

            playlist_obj["latest_saved_date"] = latest_saved_date
            playlist_obj["existing_video_ids"] = existing_video_ids
            new_video_data_dict = await fetch_playlist_items([playlist_obj])
            new_video_data = new_video_data_dict[playlist_obj["_id"]]
            if not new_video_data:
                log.info(f"[{playlist_name}] No new videos")
                return SYNC_NOOP

            self.home_state.create_video(new_video_data, playlist_obj["_id"])
            log.info(f"[{playlist_name}] Synced {len(new_video_data)} videos")
            return SYNC_OK

        except AuthError as e:
            log.error(f"[{playlist_name}] Auth error: {e}")
            return SYNC_ERROR

        except Exception as e:
            msg = str(e)
            log.info(f"[{playlist_name}] {msg}")

            # 👇 detect active-upload validation error
            if "duration_seconds" in msg and "Field required" in msg:
                log.warning(f"[{playlist_name}] Upload in progress detected, retrying soon")
                return SYNC_RETRY_SOON

            log.exception(f"[{playlist_name}] Sync failed")
            return SYNC_ERROR

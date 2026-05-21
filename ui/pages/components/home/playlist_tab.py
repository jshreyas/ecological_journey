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

    def _run_playlist_sync(self, playlist_obj: dict):

        async def run():
            spinner = ui.spinner(size="lg").props("color=primary")
            spinner.set_visibility(True)

            try:
                log.info(f"User-initiated sync for playlist: " f"{playlist_obj['name']} ({playlist_obj['_id']})")

                result = await self.sync_playlist(playlist_obj)

                if result == SYNC_OK:
                    ui.notify("Playlist synced successfully", type="positive")

                elif result == SYNC_NOOP:
                    ui.notify("No new videos to sync", type="info")

                elif result == SYNC_RETRY_SOON:
                    ui.notify(
                        "Upload still in progress — try again shortly",
                        type="warning",
                    )

                else:
                    ui.notify("Sync failed", type="negative")

            except Exception as e:
                ui.notify(f"❌ Sync failed: {str(e)}")

            finally:
                spinner.set_visibility(False)

        asyncio.create_task(run())

    def _build_playlist_rows(self, playlists, owned_ids=None, logged_in=False):
        rows = []

        owned_ids = owned_ids or set()

        for playlist in playlists:
            is_owned = playlist["_id"] in owned_ids

            rows.append(
                {
                    # "_id": playlist["_id"],
                    "name": playlist["name"],
                    "video_count": playlist.get("video_count", 0),
                    "color": playlist.get("color", "bg-gray-300"),
                    "can_sync": is_owned if logged_in else True,
                    "is_owned": is_owned,
                    "url": '<a href="https://google.com">https://google.com</a>',
                }
            )

        return rows

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

                row_data = self._build_playlist_rows(
                    playlists=all_playlists,
                    logged_in=False,
                )

                owned_ids = set()

            else:

                both = self.home_state.load_playlists_for_user()

                owned = both["owned"]
                member = both["member"]

                owned_ids = {pl["_id"] for pl in owned}

                all_playlists = owned + [p for p in member if p["_id"] not in owned_ids]

                row_data = self._build_playlist_rows(
                    playlists=all_playlists,
                    owned_ids=owned_ids,
                    logged_in=True,
                )
            # import pdb; pdb.set_trace()  # --- IGNORE ---
            grid = ui.aggrid(
                {
                    # "defaultColDef": {
                    #     "sortable": True,
                    #     "resizable": True,
                    # },
                    "columnDefs": [
                        {
                            "headerName": "Playlist",
                            "field": "name",
                            # "flex": 3,
                            # "tooltipField": "_id",
                        },
                        {
                            "headerName": "Videos",
                            "field": "video_count",
                            # "width": 120,
                        },
                        # {
                        #     # "headerName": "Color",
                        #     "field": "color",
                        #     "width": 120,
                        #     # hide raw value
                        #     "valueFormatter": "return '';",
                        #     "rowClassRules": {
                        #         "bg-red-300": "x === 'bg-red-300'",
                        #         "bg-blue-300": "x === 'bg-blue-300'",
                        #         "bg-green-300": "x === 'bg-green-300'",
                        #         "bg-yellow-300": "x === 'bg-yellow-300'",
                        #         "bg-purple-300": "x === 'bg-purple-300'",
                        #         "bg-pink-300": "x === 'bg-pink-300'",
                        #         "bg-gray-300": "x === 'bg-gray-300'",
                        #     },
                        # },
                        {
                            "field": "url",
                            # "cellRenderer": 'customButton',
                            # "cellRendererParams": { "actionType": 'delete' }
                        },
                        {
                            "headerName": "Sync",
                            "field": "can_sync",
                            "width": 110,
                            "cellRenderer": """
                                function(params) {

                                    const button = document.createElement('button');

                                    button.innerHTML = '🔄';

                                    button.className =
                                        'px-2 py-1 rounded bg-primary text-white';

                                    if (!params.data.can_sync) {
                                        button.disabled = true;
                                        button.style.opacity = '0.5';
                                    }

                                    button.addEventListener('click', () => {

                                        if (!params.data.can_sync) {
                                            return;
                                        }

                                        emitEvent('sync_playlist', params.data);
                                    });

                                    return button;
                                }
                        """,
                        },
                    ],
                    "rowData": row_data,
                    # "rowSelection": {"mode": "multiRow"},
                    "stopEditingWhenCellsLoseFocus": True,
                    "domLayout": "autoHeight",
                },
                html_columns=[2],
            ).classes("w-full")

            async def handle_sync(e):

                row = e.args

                playlist_obj = next(
                    (p for p in all_playlists if p["_id"] == row["_id"]),
                    None,
                )

                if not playlist_obj:
                    ui.notify("Playlist not found", type="negative")
                    return

                if not self.home_state.user:
                    caught_john_doe()
                    return

                if playlist_obj["_id"] not in owned_ids:
                    ui.notify(
                        "Only playlist owners can sync",
                        type="warning",
                    )
                    return

                self._run_playlist_sync(playlist_obj)

            grid.on("sync_playlist", handle_sync)
            # render_add_playlist_card()

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

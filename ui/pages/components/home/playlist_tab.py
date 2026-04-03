import asyncio

from nicegui import ui

from ui.data.crud import AuthError, load_playlists
from ui.log import log
from ui.utils.dialog_puns import caught_john_doe
from ui.utils.utils_api import create_playlist, create_video, load_playlists_for_user, load_videos
from ui.utils.youtube import fetch_playlist_items, fetch_playlist_metadata

from .state import State

SYNC_OK = "ok"
SYNC_NOOP = "noop"
SYNC_RETRY_SOON = "retry_soon"
SYNC_ERROR = "error"


async def sync_playlist(
    playlist_obj: dict,
    token: str,
) -> str:
    playlist_name = playlist_obj["name"]
    try:
        existing_videos = load_videos(playlist_obj["_id"])

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

        create_video(new_video_data, token, playlist_obj["_id"])
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


class PlaylistTab:
    """Component for displaying playlist tab"""

    def __init__(self, home_state: State):
        self.home_state = home_state
        self.container = None

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
                        playlist = create_playlist(
                            [],
                            self.home_state.user.token if self.home_state.user else None,
                            playlist_name,
                            playlist_id,
                        )
                        result = await sync_playlist(
                            playlist_obj=playlist,
                            token=self.home_state.user.token if self.home_state.user else None,
                        )
                        spinner.set_visibility(False)
                        if result == SYNC_OK:
                            ui.notify("✅ Playlist created and synced")
                        elif result == SYNC_NOOP:
                            ui.notify("ℹ️ Playlist added (no videos yet)")
                        else:
                            ui.notify("⚠️ Playlist added, sync failed")

                        self.refresh()
                        # render_dashboard()  # TODO: refresh feedtab
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

        def render_playlist_card(
            *,
            playlist: dict,
            show_sync: bool,
            on_sync_click=None,
        ):
            with ui.column().classes("w-full p-2 border border-gray-300 rounded-lg bg-white shadow-md"):
                with ui.row().classes("w-full justify-between items-center"):
                    ui.label(playlist["name"]).tooltip(playlist["_id"]).classes("text-sm font-semibold")
                    # TODO: playlist owner can change the color with color picker, update the playlist backend accordingly
                    ui.element("div").classes(f"{playlist['color']} w-3 h-3 rounded-full")

                with ui.row().classes("w-full justify-between items-center"):
                    ui.label(f"🎬 {playlist.get('video_count')}").classes("text-xs text-gray-600")

                    if show_sync and on_sync_click:
                        ui.button(
                            icon="sync",
                            on_click=on_sync_click,
                        ).props(
                            "flat dense round color=primary"
                        ).tooltip("Sync")

        with self.container:
            if not self.home_state.user:
                for playlist in load_playlists():
                    render_playlist_card(
                        playlist=playlist,
                        show_sync=True,
                        on_sync_click=lambda: caught_john_doe(),
                    )
            else:
                both = load_playlists_for_user(self.home_state.user.id)
                owned, member = both["owned"], both["member"]
                owned_ids = {pl["_id"] for pl in owned}
                all_playlists = owned + [p for p in member if p["_id"] not in owned_ids]

                def on_user_sync_click(playlist_obj: dict, token: str):
                    playlist_id = playlist_obj["_id"]
                    playlist_name = playlist_obj["name"]

                    async def run():
                        try:
                            log.info(f"User-initiated sync for playlist: {playlist_name} ({playlist_id})")
                            result = await sync_playlist(
                                playlist_obj=playlist_obj,
                                token=token,
                            )

                            with self.container:
                                if result == SYNC_OK:
                                    ui.notify("Playlist synced successfully", type="positive")
                                elif result == SYNC_NOOP:
                                    ui.notify("No new videos to sync", type="info")
                                elif result == SYNC_RETRY_SOON:
                                    ui.notify("Upload still in progress — try again shortly", type="warning")
                                else:
                                    ui.notify("Sync failed", type="negative")

                        except Exception as e:
                            with self.container:
                                ui.notify(f"Sync failed: {e}", type="negative")

                    log.info(f"Preparing to sync playlist: {playlist_name} ({playlist_id})")
                    return run

                def on_sync_click(playlist_obj, token):
                    spinner = ui.spinner(size="lg").props("color=primary")
                    spinner.set_visibility(True)

                    async def do_sync():
                        try:
                            await on_user_sync_click(playlist_obj, token)()
                        except Exception as e:
                            ui.notify(f"❌ Sync failed: {str(e)}")
                        finally:
                            spinner.set_visibility(False)
                            self.refresh()
                            # render_dashboard()  # TODO: refresh feedtab

                    ui.timer(0.1, lambda: asyncio.create_task(do_sync()), once=True)

                for playlist in all_playlists:
                    is_owned = playlist["_id"] in owned_ids

                    render_playlist_card(
                        playlist=playlist,
                        show_sync=is_owned,
                        on_sync_click=(
                            lambda p=playlist: on_sync_click(p, self.home_state.user.token) if is_owned else None
                        ),
                    )

            render_add_playlist_card()

import asyncio
from collections import Counter
from datetime import datetime

from data.crud import AuthError, load_playlists
from dotenv import load_dotenv
from log import log
from nicegui import ui
from pages.components.home.calendar_component import calendar_container
from utils.dialog_puns import caught_john_doe
from utils.fetch_videos import fetch_playlist_metadata
from utils.user_context import User, with_user_context
from utils.utils import group_videos_by_day
from utils.utils_api import (
    create_playlist,
    create_team,
    create_video,
    fetch_teams_for_user,
    load_playlists_for_user,
    load_videos,
)

load_dotenv()


def render_add_playlist_card(parent, user: User | None, refresh_playlists, render_dashboard):
    with parent:
        with ui.card().classes("w-full p-4 border border-gray-300 rounded-lg bg-white shadow-md gap-3"):
            ui.label("➕ Playlist by ID").classes("text-md font-bold")
            playlist_verified = {"status": False}
            playlist_id_input = ui.input("YouTube Playlist ID").classes("w-full text-sm")

            def verify_playlist():
                playlist_id = playlist_id_input.value.strip()
                if not playlist_id:
                    ui.notify("❌ Please enter a Playlist ID.", type="warning")
                    fetch_button.disable()
                    playlist_verified["status"] = False
                    return
                metadata = fetch_playlist_metadata(playlist_id)
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

            def fetch_playlist_videos():
                if not playlist_verified["status"]:
                    ui.notify("❌ Please verify the playlist first.", type="warning")
                    return
                playlist_id = playlist_id_input.value.strip()
                metadata = fetch_playlist_metadata(playlist_id)
                playlist_name = metadata.get("title", playlist_id)
                ui.notify(f"Fetching videos for playlist: {playlist_name}")
                spinner = ui.spinner(size="lg").props("color=primary")
                ui.timer(0.1, lambda: spinner.set_visibility(True), once=True)

                def task():
                    from utils.fetch_videos import fetch_playlist_items

                    create_playlist(
                        fetch_playlist_items(playlist_id),
                        user.token if user else None,
                        playlist_name,
                        playlist_id,
                    )
                    spinner.set_visibility(False)
                    ui.notify("✅ Playlist fetched and added successfully!")
                    refresh_playlists()
                    render_dashboard()
                    playlist_id_input.value = ""
                    fetch_button.disable()
                    playlist_verified["status"] = False

                ui.timer(0.2, task, once=True)

            playlist_id_input.on("change", on_input_change)
            with ui.row().classes("w-full justify-start gap-4"):
                ui.button(
                    on_click=(caught_john_doe if not user else verify_playlist),
                    icon="check_circle",
                ).props(
                    "flat round"
                ).tooltip("Verify Playlist")
                fetch_button = ui.button(icon="download").props("flat round").tooltip("Fetch Videos")
                fetch_button.disable()
                fetch_button.on("click", fetch_playlist_videos)


def render_playlists_list(parent, user: User | None, refresh_playlists, render_dashboard):
    parent.clear()
    if not user:
        for playlist in load_playlists():
            with parent:
                with ui.column().classes("w-full p-4 border border-gray-300 rounded-lg bg-white shadow-md"):
                    ui.label(playlist["name"]).tooltip(playlist["_id"]).classes("text-sd font-semibold")
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label(f"🎬 Videos: {len(playlist.get('videos'))}").classes("text-xs text-gray-600")
                        ui.button(
                            icon="sync",
                            on_click=lambda: caught_john_doe(),
                        ).props(
                            "flat dense round color=primary"
                        ).tooltip("Sync")
    else:
        both = load_playlists_for_user(user.id)
        owned, member = both["owned"], both["member"]
        owned_ids = {pl["_id"] for pl in owned}
        all_playlists = owned + [p for p in member if p["_id"] not in owned_ids]

        def on_user_sync_click(
            parent,
            playlist_obj: dict,
            token: str,
        ):
            playlist_id = playlist_obj["_id"]
            playlist_name = playlist_obj["name"]

            async def run():
                try:
                    log.info(f"User-initiated sync for playlist: {playlist_name} ({playlist_id})")
                    result = await sync_playlist(
                        playlist_obj=playlist_obj,
                        token=token,
                    )
                    with parent:
                        if result == SYNC_OK:
                            ui.notify("Playlist synced successfully", type="positive")

                        elif result == SYNC_NOOP:
                            ui.notify("No new videos to sync", type="info")

                        elif result == SYNC_RETRY_SOON:
                            ui.notify("Upload still in progress — try again shortly", type="warning")

                        else:
                            ui.notify("Sync failed", type="negative")

                except Exception as e:
                    with parent:
                        ui.notify(f"Sync failed: {e}", type="negative")

            log.info(f"Preparing to sync playlist: {playlist_name} ({playlist_id})")
            return run

        def on_sync_click(parent, playlist_obj, token):
            spinner = ui.spinner(size="lg").props("color=primary")
            spinner.set_visibility(True)

            async def do_sync():
                try:
                    await on_user_sync_click(parent, playlist_obj, token)()
                except Exception as e:
                    ui.notify(f"❌ Sync failed: {str(e)}")
                finally:
                    spinner.set_visibility(False)
                    refresh_playlists()
                    render_dashboard()

            ui.timer(0.1, lambda: asyncio.create_task(do_sync()), once=True)

        for playlist in all_playlists:
            with parent:
                with ui.column().classes("w-full p-4 border border-gray-300 rounded-lg bg-white shadow-md gap-2"):
                    ui.label(playlist["name"]).tooltip(playlist["_id"]).classes("text-md font-semibold")
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label(f"🎬 Videos: {len(playlist.get('videos'))}").classes("text-sm text-gray-600")
                        if playlist["_id"] in owned_ids:
                            ui.button(
                                icon="sync",
                                on_click=lambda playlist_obj=playlist: on_sync_click(parent, playlist_obj, user.token),
                            ).props("flat dense round color=primary").tooltip("Sync")
    # Always render the add playlist card at the end
    render_add_playlist_card(parent, user, refresh_playlists, render_dashboard)


def render_dashboard(parent):
    parent.clear()
    videos = load_videos()
    if not videos:
        with parent:
            with ui.card().classes("p-4 text-center"):
                ui.label("⚠️ No videos found! Start by adding a playlist.").classes("text-md")
        return
    grouped_videos_by_day = group_videos_by_day(videos)
    dates = [datetime.strptime(v["date"], "%Y-%m-%dT%H:%M:%SZ") for v in videos]
    with parent:
        calendar_container(grouped_videos_by_day)
        ui.separator().classes("my-4 w-full")
        date_counts = Counter(d.date() for d in dates)
        sorted_dates = sorted(date_counts.keys())
        chart_data = {
            "labels": [d.strftime("%b %d, %Y") for d in sorted_dates],
            "datasets": [
                {
                    "label": "Video Count",
                    "data": [date_counts[d] for d in sorted_dates],
                    "type": "bar",
                    "itemStyle": {"color": "#4CAF50"},
                }
            ],
        }
        ui.echart(
            {
                "title": {
                    "text": "Activity Over Time",
                    "left": "center",
                    "textStyle": {"fontSize": 18, "fontWeight": "bold"},
                },
                "tooltip": {
                    "trigger": "axis",
                    "axisPointer": {"type": "shadow"},
                    "formatter": "{b}: {c} videos",
                },
                "grid": {
                    "left": "10%",
                    "right": "10%",
                    "bottom": "15%",
                    "containLabel": True,
                },
                "xAxis": {
                    "type": "category",
                    "data": chart_data["labels"],
                    "axisLabel": {
                        "rotate": 45,
                        "fontSize": 12,
                    },
                    "axisLine": {"lineStyle": {"color": "#888"}},
                },
                "yAxis": {
                    "type": "value",
                    "axisLabel": {
                        "fontSize": 12,
                        "formatter": "{value}",
                    },
                    "axisLine": {"lineStyle": {"color": "#888"}},
                    "splitLine": {"lineStyle": {"type": "dashed", "color": "#ddd"}},
                },
                "series": [
                    {
                        "type": "bar",
                        "data": chart_data["datasets"][0]["data"],
                        "barWidth": "50%",
                    }
                ],
            }
        ).classes("w-full h-80")


@with_user_context
def home_page(user: User | None):
    with ui.splitter(value=25).classes("w-full h-[600px] gap-4") as splitter:
        with splitter.before:
            with ui.tabs().classes("w-full") as tabs:
                tab_playlists = ui.tab("🎵 Playlists")
                tab_teams = ui.tab("👥 Teams")
            with ui.tab_panels(tabs, value=tab_playlists).classes("w-full h-full"):
                with ui.tab_panel(tab_playlists) as playlists_container:

                    def refresh_playlists():
                        render_playlists_list(
                            playlists_container,
                            user,
                            refresh_playlists,
                            lambda: render_dashboard(dashboard_column),
                        )

                    refresh_playlists()
                with ui.tab_panel(tab_teams) as teams_container:

                    def refresh_teams():
                        teams_container.clear()
                        if not user:
                            both = fetch_teams_for_user_jd(44)
                        else:
                            both = fetch_teams_for_user(user.id)
                        owned, member = both["owned"], both["member"]
                        owned_ids = {t["_id"] for t in owned}
                        all_teams = owned + [t for t in member if t["_id"] not in owned_ids]
                        with ui.column().classes(
                            "w-full p-4 border border-gray-300 rounded-lg bg-white shadow-md gap-3"
                        ):
                            with ui.row().classes("w-full justify-between items-center"):

                                def create_new_team():
                                    name = team_name_input.value.strip()
                                    if not name:
                                        ui.notify("Please enter a team name.", type="warning")
                                        return
                                    create_team(name, user.token, user.id)
                                    ui.notify(f'Team "{name}" created successfully!')
                                    refresh_teams()
                                    team_name_input.value = ""

                                ui.label("➕ Team").classes("text-sd font-bold")
                                ui.button(
                                    on_click=(caught_john_doe if not user else create_new_team),
                                    icon="save",
                                ).props("flat round").tooltip("Create Team")
                            team_name_input = ui.input("Team Name").classes("w-full")
                        for team in all_teams:
                            with teams_container:
                                with ui.column().classes(
                                    "w-full p-4 border border-gray-300 rounded-lg bg-white shadow-md"
                                ):
                                    with ui.row().classes("w-full justify-between items-center"):
                                        ui.label(team["name"]).classes("text-lg font-bold")
                                        if team["_id"] in owned_ids:
                                            with ui.row().classes("w-full"):
                                                ui.button(
                                                    icon="person_add",
                                                    on_click=lambda t=team: open_add_user_modal(t),
                                                ).props("flat round").tooltip("Add User")
                                                ui.button(
                                                    icon="playlist_add",
                                                    on_click=lambda t=team: open_add_playlist_modal(t),
                                                ).props("flat round").tooltip("Add Playlist")
                                                ui.button(
                                                    icon="manage_accounts",
                                                    on_click=lambda t=team: open_team_modal(t),
                                                ).props("flat round").tooltip("Manage Team")
                                    with ui.row().classes("w-full justify-between items-center"):
                                        ui.label(f"👥 {len(team.get('member_ids', []))}").classes(
                                            "text-sm text-gray-600"
                                        )
                                        ui.label(f"🎵 {team.get('playlist_count', 0)}").classes("text-sm text-gray-600")

                    refresh_teams()
        with splitter.after:
            with ui.column().classes("w-full") as dashboard_column:

                def render_dashboard_wrapper():
                    render_dashboard(dashboard_column)

                render_dashboard_wrapper()


# --- Stubbed Actions ---
def fetch_teams_for_user_jd(user_id):
    # Sample data to simulate backend result
    return {
        "owned": [
            {
                "_id": "team1",
                "name": "Mat Lab",
                "owner_id": user_id,
                "playlist_count": 2,
                "member_ids": ["user2", "user3", "user3"],
            }
        ],
        "member": [
            {
                "_id": "team2",
                "name": "Mao Pelo Pe",
                "playlist_count": 5,
                "owner_id": "another_user",
                "member_ids": [
                    user_id,
                    "user4",
                    "user22",
                    "user31",
                    "user2",
                    "user3",
                    "user4",
                ],
            }
        ],
    }


def open_add_user_modal(team):
    with ui.dialog() as dialog, ui.card().classes("w-[30rem]"):
        ui.label(f'➕ Add user to {team["name"]}').classes("text-lg font-semibold")

        # Stubbed user list (replace with real API call later)
        all_users = [
            {"email": "alice@example.com", "name": "Alice"},
            {"email": "bob@example.com", "name": "Bob"},
            {"email": "charlie@example.com", "name": "Charlie"},
        ]

        # Map email -> display name (email)
        user_map = {u["email"]: f'{u["name"]} ({u["email"]})' for u in all_users}

        user_select = ui.select(user_map, label="Select User")

        def add_user():
            email = user_select.value
            if not email:
                ui.notify("⚠️ Please select a user.", type="warning")
                return
            log.info(f"Adding user {email} to team {team['_id']}")
            ui.notify(f"✅ Added {email} to {team['name']}")
            dialog.close()

        with ui.row().classes("gap-2 mt-3"):
            ui.button("Add User", on_click=add_user).props("color=primary")
            ui.button("Cancel", on_click=dialog.close).props("flat")

    dialog.open()


def open_add_playlist_modal(team):
    with ui.dialog() as dialog, ui.card().classes("w-[30rem]"):
        ui.label(f'🎵 Add playlist to {team["name"]}').classes("text-lg font-semibold")

        # Stubbed playlist list (replace with call to load_playlists_for_user)
        user_playlists = [
            {"_id": "pl1", "name": "Top Transitions"},
            {"_id": "pl2", "name": "Submission Chains"},
        ]

        playlist_select = ui.select([pl["name"] for pl in user_playlists], label="Select Playlist")

        def add_playlist():
            selected_name = playlist_select.value
            if not selected_name:
                ui.notify("⚠️ Please select a playlist.", type="warning")
                return
            selected = next(pl for pl in user_playlists if pl["name"] == selected_name)
            log.info(f"Assigning playlist '{selected['_id']}' to team '{team['_id']}'")
            ui.notify(f"✅ Added '{selected_name}' to team {team['name']}")
            dialog.close()

        with ui.row().classes("gap-2 mt-3"):
            ui.button("Add Playlist", on_click=add_playlist).props("color=primary")
            ui.button("Cancel", on_click=dialog.close).props("flat")

    dialog.open()


def open_team_modal(team):
    with ui.dialog() as dialog, ui.card().classes("w-[40rem]"):
        ui.label(f"👥 Team: {team['name']}").classes("text-lg font-semibold")

        members = [
            {
                "name": "Alice",
                "email": "alice@example.com",
                "role": "member",
                "joined": "2024-01-10",
            },
            {
                "name": "Bob",
                "email": "bob@example.com",
                "role": "member",
                "joined": "2024-02-12",
            },
        ]

        member_container = ui.column().classes("gap-2 mt-2")

        def refresh():
            member_container.clear()
            for member in members:
                with member_container:
                    with ui.row().classes("items-center justify-between w-full"):
                        ui.label(
                            f"{member['name']} ({member['email']}) - \
                            {member['role']}, joined: {member['joined']}"
                        )
                        ui.button("Remove", on_click=lambda m=member: remove_member(m)).props("flat dense").classes(
                            "text-red-500"
                        )

        def remove_member(member):
            members.remove(member)
            ui.notify(f'Removed {member["name"]}')
            refresh()

        refresh()

        ui.button("Close", on_click=dialog.close).classes("mt-4")

    dialog.open()


SYNC_OK = "ok"
SYNC_NOOP = "noop"
SYNC_RETRY_SOON = "retry_soon"
SYNC_ERROR = "error"


async def sync_playlist(
    playlist_obj: dict,
    token: str,
) -> str:
    from utils.youtube import fetch_playlist_items

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


def create_team_modal():
    log.info("Opening modal to create a new team")


def view_playlist_videos(playlist):
    log.info(f"Viewing videos for playlist: {playlist['title']}")

import asyncio
from collections import Counter
from datetime import datetime, timedelta

from data.crud import load_playlists
from log import log
from nicegui import events, ui
from pages.components.home.calendar_component import calendar_container
from starlette.formparsers import MultiPartParser
from utils.dialog_puns import caught_john_doe
from utils.fetch_videos import fetch_playlist_items, fetch_playlist_metadata
from utils.peertube_api import PeerTubeClient
from utils.user_context import User, with_user_context
from utils.utils import group_videos_by_day, parse_flexible_datetime
from utils.utils_api import (
    create_playlist,
    create_team,
    create_video,
    fetch_teams_for_user,
    load_playlists_for_user,
    load_videos,
)

# TODO: verify its usage and purpose
MultiPartParser.spool_max_size = 1024 * 1024 * 50  # 50 MB
client = PeerTubeClient()


def render_add_playlist_card(parent, user: User | None, refresh_playlists, render_dashboard):
    with parent:
        with ui.column().classes("w-full p-4 border border-gray-300 rounded-lg bg-white shadow-md gap-2"):
            # with ui.card().classes("w-full p-4 border border-gray-300 rounded-lg bg-white shadow-md gap-3"):
            with ui.row().classes("w-full justify-between items-center"):

                def on_input_change(e):
                    # Update label dynamically based on toggle state
                    if e.value:
                        playlist_id_input.label = "YouTube Playlist ID"
                    else:
                        playlist_id_input.label = "PeerTube Playlist ID"

                ui.label("➕ Playlist by ID").classes("text-md font-bold")
                youtube_toggle = ui.toggle({True: "YT", False: "PT"}, value=True, on_change=on_input_change).props(
                    "size=xs"
                )

            playlist_verified = {"status": False}
            playlist_id_input = ui.input("YouTube Playlist ID").classes("w-full text-sm")

            async def verify_playlist():
                playlist_id = playlist_id_input.value.strip()
                if not playlist_id:
                    ui.notify("❌ Please enter a Playlist ID.", type="warning")
                    fetch_button.disable()
                    playlist_verified["status"] = False
                    return

                if youtube_toggle.value:
                    metadata = fetch_playlist_metadata(playlist_id)
                else:
                    metadata = await client.get_playlist(playlist_id)

                if metadata:
                    playlist_name = metadata.get("title") if youtube_toggle.value else metadata.get("displayName")
                    ui.notify(f"✅ Playlist verified: {playlist_name}", type="success")
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

                if youtube_toggle.value:
                    metadata = fetch_playlist_metadata(playlist_id)
                    playlist_name = metadata.get("title", playlist_id)
                else:
                    metadata = await client.get_playlist(playlist_id)
                    playlist_name = metadata.get("displayName", playlist_id)

                ui.notify(f"Fetching videos for playlist: {playlist_name}")
                spinner = ui.spinner(size="lg").props("color=primary")
                ui.timer(0.1, lambda: spinner.set_visibility(True), once=True)

                async def task():
                    if youtube_toggle.value:
                        video_data = fetch_playlist_items(playlist_id)
                        ui.notify(f"Fetched {len(video_data)} videos from YouTube playlist.")
                    else:
                        # TODO: handle negative cases
                        video_data = await client.get_playlist_videos(playlist_id)
                        ui.notify(f"Fetched {len(video_data)} videos from PeerTube playlist.")

                    create_playlist(
                        video_data,
                        user.token if user else None,
                        playlist_name,
                        playlist_id,
                        source="youtube" if youtube_toggle.value else "peertube",
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

    from data.crud import load_uploads

    def show_logs(upload_id, filename, **kwargs):

        from utils.cache import cache_lrange

        with ui.dialog() as log_dialog:
            with ui.card():
                ui.label(f"📜 Logs for {filename}")
                logs = ui.log().classes("w-full h-64 bg-black text-primary p-2 font-mono text-xs overflow-y-auto")

                async def refresh_logs():
                    while True:
                        resp = cache_lrange(f"upload:{upload_id}:logs", 0, -1)
                        if resp:
                            logs.clear()
                            logs.push(resp)
                        else:
                            ui.notify("✅ Upload successful")
                            break
                        await asyncio.sleep(2)

                if "status" in kwargs and kwargs["status"] == "completed" and "logs" in kwargs and kwargs["logs"]:
                    logs.push(kwargs["logs"])
                else:
                    ui.timer(0.1, refresh_logs, once=True)

        log_dialog.open()

    def toggle_fab():
        nonlocal expanded
        expanded = not expanded
        for b in buttons:
            b.visible = expanded

    with ui.column().classes("fixed h-[600px] bottom-4 right-4 items-end overflow-y-auto"):
        with ui.page_sticky(position="bottom-left", x_offset=18, y_offset=18):
            with ui.column().classes("items-center overflow-y-auto"):
                buttons = []
                for each in load_uploads():
                    if each.get("status") == "uploading":
                        color = "primary"
                    elif each.get("status") == "failed":
                        color = "red"
                    else:
                        color = "secondary"
                    buttons.append(
                        ui.button(icon="file_copy", on_click=lambda _, upload_dict=each: show_logs(**upload_dict))
                        .props(f"round color={color}")
                        .tooltip(f'{each.get("filename")}')
                    )
                ui.button(icon="upload_file", on_click=toggle_fab).props("round fab").tooltip("Uploads")

        for b in buttons:
            b.visible = False  # start hidden

        expanded = False

    def upload_and_sync_videos(playlist_id, token, playlist_name, play_id):
        with ui.dialog() as dialog:
            with ui.card():
                ui.label(f"📤 Upload to {playlist_name}").classes("text-md font-semibold")

                async def handle_upload(e: events.UploadEventArguments):
                    import uuid

                    upload_id = str(uuid.uuid4())
                    asyncio.create_task(
                        client.upload_and_attach_to_playlist(
                            file_input=e.content, name=e.name, file_input_name=e.name, upload_id=upload_id
                        )
                    )
                    # Step 1: send to backend (enqueue)
                    ui.notify(f"✅ Upload queued: {upload_id}")

                    # Step 2: show modal to view logs
                    ui.button(
                        "View Logs", on_click=lambda _, upload_id=upload_id, name=e.name: show_logs(upload_id, name)
                    ).props("color=primary")

                ui.upload(on_upload=handle_upload, auto_upload=True, multiple=False)
        dialog.open()

    # def upload_and_sync_videos(playlist_id, token, playlist_name, play_id):
    #     with ui.dialog() as dialog:
    #         with ui.card():

    #             async def handle_upload(e: events.UploadEventArguments):
    #                 try:
    #                     # Step 2: perform backend → PeerTube upload
    #                     response = await client.upload_and_attach_to_playlist(
    #                         e.content,
    #                         name=f"{e.name}",
    #                         file_input_name=e.name,
    #                     )
    #                     print("DEBUG: PeerTube upload response:", response)
    #                     ui.notify(f"🎉 PeerTube upload complete for {e.name}: {response}", color="green")
    #                     # if await sync_playlist(playlist_id, token, playlist_name, play_id, "peertube"):
    #                     # refresh_playlists()
    #                     # render_dashboard()
    #                     # dialog.close()
    #                 except Exception as ex:
    #                     ui.notify(f"Error uploading {e.name}: {ex}", color="red")
    #                     print(f"Error uploading {e.name}: {ex}")

    #             ui.upload(on_upload=handle_upload, auto_upload=True, multiple=True).classes("max-w-full")
    #     dialog.open()

    if not user:
        for playlist in load_playlists():
            with parent:
                with ui.column().classes("w-full p-4 border border-gray-300 rounded-lg bg-white shadow-md"):
                    with ui.row().classes("w-full justify-between items-center"):
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

        def on_sync_click(playlist_id, token, playlist_name, play_id, sourcee):
            def task():
                spinner = ui.spinner(size="lg").props("color=primary")
                spinner.set_visibility(True)

                async def do_sync():
                    try:
                        await sync_playlist(playlist_id, token, playlist_name, play_id, sourcee)
                    except Exception as e:
                        ui.notify(f"❌ Sync failed: {str(e)}")
                    finally:
                        spinner.set_visibility(False)
                        refresh_playlists()
                        render_dashboard()

                ui.timer(0.2, do_sync, once=True)

            task()

        for playlist in all_playlists:
            with parent:
                with ui.column().classes("w-full p-4 border border-gray-300 rounded-lg bg-white shadow-md gap-2"):
                    ui.label(playlist["name"]).tooltip(playlist["_id"]).classes("text-md font-semibold")
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label(f"🎬 Videos: {len(playlist.get('videos'))}").classes("text-sm text-gray-600")
                        with ui.row().classes("justify-end items-center"):
                            if playlist["_id"] in owned_ids:
                                if playlist.get("source") == "peertube":
                                    ui.button(
                                        icon="upload",
                                        on_click=lambda pid=playlist["_id"], name=playlist["name"], play_id=playlist[
                                            "playlist_id"
                                        ]: upload_and_sync_videos(pid, user.token, name, play_id),
                                    ).props("flat dense round color=primary").tooltip("Upload")
                                ui.button(
                                    icon="sync",
                                    on_click=lambda pid=playlist["_id"], name=playlist["name"], play_id=playlist[
                                        "playlist_id"
                                    ]: on_sync_click(pid, user.token, name, play_id, playlist.get("source", "youtube")),
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
    # dates = [datetime.strptime(v["date"], "%Y-%m-%dT%H:%M:%SZ") for v in videos]
    dates = [parse_flexible_datetime(v["date"]) for v in videos]
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


async def sync_playlist(playlist_id, token, playlist_name, play_id, sources="youtube"):
    try:
        # Step 1: Fetch existing videos from DB
        existing_videos = load_videos(playlist_id)
        if existing_videos:
            latest_saved_date_str = max(video["date"] for video in existing_videos)
            latest_saved_date = datetime.fromisoformat(latest_saved_date_str.replace("Z", "+00:00")) - timedelta(days=1)
            existing_video_ids = {video["video_id"] for video in existing_videos}
        else:
            latest_saved_date = None
            existing_video_ids = set()

        # Step 2: Fetch only new videos from YouTube
        if sources == "youtube":
            latest_video_data = fetch_playlist_items(play_id, latest_saved_date)
        else:
            latest_video_data = await client.get_playlist_videos(play_id)
        new_video_data = [video for video in latest_video_data if video["video_id"] not in existing_video_ids]
        if not new_video_data:
            ui.notify("✅ Playlist is already up to date!")
            return False

        # Step 3: Append new videos
        create_video(new_video_data, token, play_id)
        ui.notify(f'✅ Synced {len(new_video_data)} new videos to "{playlist_name}".')
        return True

    except Exception as exc:
        log.error(f"❌ Sync failed: {str(exc)}")
        ui.notify(f"❌ Sync failed: {str(exc)}")


def create_team_modal():
    log.info("Opening modal to create a new team")


def view_playlist_videos(playlist):
    log.info(f"Viewing videos for playlist: {playlist['title']}")

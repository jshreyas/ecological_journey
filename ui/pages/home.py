from collections import Counter
from datetime import datetime

from nicegui import app, ui
from pages.home_components.calendar_component import calendar_container
from utils.dialog_puns import caught_john_doe
from utils.fetch_videos import fetch_playlist_items, fetch_playlist_metadata
from utils.utils import group_videos_by_day
from utils.utils_api import (
    create_playlist,
    create_team,
    create_video,
    fetch_teams_for_user,
    load_playlists,
    load_playlists_for_user,
    load_videos,
)


def render_add_playlist_card(parent, user_token, username, refresh_playlists, render_dashboard):
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
                    create_playlist(
                        fetch_playlist_items(playlist_id),
                        user_token,
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
                    on_click=(caught_john_doe if not username else verify_playlist),
                    icon="check_circle",
                ).props(
                    "flat round"
                ).tooltip("Verify Playlist")
                fetch_button = ui.button(icon="download").props("flat round").tooltip("Fetch Videos")
                fetch_button.disable()
                fetch_button.on("click", fetch_playlist_videos)


def render_playlists_list(parent, username, user_token, user_id, refresh_playlists, render_dashboard):
    parent.clear()
    if not username:
        playlists = load_playlists()
        for playlist in playlists:
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
        both = load_playlists_for_user(user_id)
        owned, member = both["owned"], both["member"]
        owned_ids = {pl["_id"] for pl in owned}
        all_playlists = owned + [p for p in member if p["_id"] not in owned_ids]

        def on_sync_click(playlist_id, token, playlist_name, play_id):
            def task():
                spinner = ui.spinner(size="lg").props("color=primary")
                spinner.set_visibility(True)

                def do_sync():
                    try:
                        sync_playlist(playlist_id, token, playlist_name, play_id)
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
                        if playlist["_id"] in owned_ids:
                            ui.button(
                                icon="sync",
                                on_click=lambda pid=playlist["_id"], name=playlist["name"], play_id=playlist[
                                    "playlist_id"
                                ]: on_sync_click(pid, user_token, name, play_id),
                            ).props("flat dense round color=primary").tooltip("Sync")
    # Always render the add playlist card at the end
    render_add_playlist_card(parent, user_token, username, refresh_playlists, render_dashboard)


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


@ui.page("/home")
def home_page():
    # TODO: this user data can be cleaned up a little
    username = app.storage.user.get("user", None)
    user_token = app.storage.user.get("token", None)
    user_id = app.storage.user.get("id", None)
    with ui.splitter(value=25).classes("w-full h-auto gap-4") as splitter:
        with splitter.before:
            with ui.tabs().classes("w-full") as tabs:
                tab_playlists = ui.tab("🎵 Playlists")
                tab_teams = ui.tab("👥 Teams")
            with ui.tab_panels(tabs, value=tab_playlists).classes("w-full h-full"):
                with ui.tab_panel(tab_playlists) as playlists_container:

                    def refresh_playlists():
                        render_playlists_list(
                            playlists_container,
                            username,
                            user_token,
                            user_id,
                            refresh_playlists,
                            lambda: render_dashboard(dashboard_column),
                        )

                    refresh_playlists()
                with ui.tab_panel(tab_teams) as teams_container:

                    def refresh_teams():
                        teams_container.clear()
                        if not username:
                            both = fetch_teams_for_user_jd(44)
                        else:
                            both = fetch_teams_for_user(user_id)
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
                                    create_team(name, user_token, user_id)
                                    ui.notify(f'Team "{name}" created successfully!')
                                    refresh_teams()
                                    team_name_input.value = ""

                                ui.label("➕ Team").classes("text-sd font-bold")
                                ui.button(
                                    on_click=(caught_john_doe if not username else create_new_team),
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
            print(f"Adding user {email} to team {team['_id']}")
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
            print(f"Assigning playlist '{selected['_id']}' to team '{team['_id']}'")
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


def sync_playlist(playlist_id, token, playlist_name, play_id):
    try:
        # Step 1: Fetch existing videos from DB
        existing_videos = load_videos(playlist_id)
        if existing_videos:
            latest_saved_date_str = max(video["date"] for video in existing_videos)
            latest_saved_date = datetime.fromisoformat(latest_saved_date_str.replace("Z", "+00:00"))
            existing_video_ids = {video["video_id"] for video in existing_videos}
        else:
            latest_saved_date = None
            existing_video_ids = set()

        # Step 2: Fetch only new videos from YouTube
        latest_video_data = fetch_playlist_items(play_id, latest_saved_date)
        new_video_data = [video for video in latest_video_data if video["video_id"] not in existing_video_ids]

        if not new_video_data:
            ui.notify("✅ Playlist is already up to date!")
            return

        # Step 3: Append new videos
        create_video(new_video_data, token, playlist_name)
        ui.notify(f'✅ Synced {len(new_video_data)} new videos to "{playlist_name}".')

    except Exception as e:
        print(f"❌ Sync failed: {str(e)}")
        ui.notify(f"❌ Sync failed: {str(e)}")


def create_team_modal():
    print("Opening modal to create a new team")


def view_playlist_videos(playlist):
    print(f"Viewing videos for playlist: {playlist['title']}")

from nicegui import ui, app
from dialog_puns import caught_john_doe
from fetch_videos import fetch_playlist_items, fetch_playlist_metadata
from utils_api import create_video, load_playlists, load_videos, create_playlist, load_playlists_for_user, create_team, fetch_teams_for_user
import datetime
from collections import Counter
from calendar_component import calendar_container
from utils import group_videos_by_day


@ui.page('/home')
def home_page():
    #TODO: this user data can be cleaned up a little
    username = app.storage.user.get("user", None)
    user_token = app.storage.user.get("token", None)
    user_id = app.storage.user.get("id", None)
    if not username:
        user = {"id": 1, "name": "John Doe"}
    else:
        user = {"id": 1, "name": username}
    all_videos = load_videos()
    grouped_videos_by_day = group_videos_by_day(all_videos)

    with ui.splitter(value=25).classes('w-full h-auto gap-4 mt-2') as splitter:

        with splitter.before:
            with ui.column().classes('w-full h-full p-2 bg-gray-100 rounded-md shadow-md gap-4'):
                # === Section: YouTube Playlists as Cards ===
                ui.label(f"🎵 {user['name']}'s Playlists").classes('text-lg font-bold')

                playlists_column = ui.column().classes('w-full')

                def refresh_playlists():
                    playlists_column.clear()

                    if not username:
                        playlists = load_playlists()
                        for playlist in playlists:
                            with playlists_column:
                                with ui.column().classes('w-full p-4 border border-gray-300 rounded-lg bg-white shadow-md'):
                                    ui.label(playlist['name']).tooltip(playlist['_id']).classes('text-sd font-semibold')
                                    with ui.row().classes('w-full justify-between items-center'):
                                        ui.label(f"🎬 Videos: {len(playlist.get('videos'))}").classes('text-xs text-gray-600')
                                        ui.button(icon='sync', on_click=lambda: caught_john_doe()).props('flat dense round color=primary').tooltip('Sync')
                    else:
                        both = load_playlists_for_user(user_id)
                        owned, member = both["owned"], both["member"]
                        owned_ids = {pl['_id'] for pl in owned}
                        all_playlists = owned + [p for p in member if p['_id'] not in owned_ids]

                        def on_sync_click(playlist_id, token, playlist_name, play_id):
                            def task():
                                spinner = ui.spinner(size='lg').props('color=primary')
                                spinner.set_visibility(True)

                                def do_sync():
                                    try:
                                        sync_playlist(playlist_id, token, playlist_name, play_id)
                                    except Exception as e:
                                        ui.notify(f'❌ Sync failed: {str(e)}')
                                    finally:
                                        spinner.set_visibility(False)
                                        refresh_playlists()
                                        render_dashboard()

                                ui.timer(0.2, do_sync, once=True)

                            task()

                        for playlist in all_playlists:
                            with playlists_column:
                                with ui.column().classes('w-full p-4 border border-gray-300 rounded-lg bg-white shadow-md gap-2'):
                                    ui.label(playlist['name']).tooltip(playlist['_id']).classes('text-md font-semibold')
                                    with ui.row().classes('w-full justify-between items-center'):
                                        ui.label(f"🎬 Videos: {len(playlist.get('videos'))}").classes('text-sm text-gray-600')
                                        if playlist['_id'] in owned_ids:
                                            ui.button(
                                                icon='sync',
                                                on_click=lambda pid=playlist['_id'], name=playlist['name'], play_id=playlist['playlist_id']: on_sync_click(pid, user_token, name, play_id)
                                            ).props('flat dense round color=primary').tooltip('Sync')
                refresh_playlists()

                # === Section: Add Playlist by ID (Card) ===
                with ui.column().classes('w-full p-4 border border-gray-300 rounded-lg bg-white shadow-md gap-3'):
                    ui.label('➕ Add Playlist by ID').classes('text-lg font-bold')

                    playlist_verified = {'status': False}

                    def verify_playlist():
                        playlist_id = playlist_id_input.value.strip()
                        if not playlist_id:
                            playlist_title_label.text = 'Please enter a Playlist ID.'
                            fetch_button.disable()
                            playlist_verified['status'] = False
                            return

                        metadata = fetch_playlist_metadata(playlist_id)
                        if metadata and 'title' in metadata:
                            playlist_title_label.text = f'Found YouTube Playlist: {metadata["title"]}'
                            fetch_button.enable()
                            playlist_verified['status'] = True
                        else:
                            playlist_title_label.text = 'Invalid Playlist ID or playlist not found.'
                            fetch_button.disable()
                            playlist_verified['status'] = False

                    def on_input_change():
                        playlist_title_label.text = ''
                        fetch_button.disable()
                        playlist_verified['status'] = False

                    def fetch_playlist_videos(playlist_id, token):
                        if not playlist_verified['status']:
                            ui.notify('❌ Please verify the playlist first.', type='warning')
                            return

                        metadata = fetch_playlist_metadata(playlist_id)
                        playlist_name = metadata.get('title', playlist_id)

                        ui.notify(f'Fetching videos for playlist: {playlist_name}')
                        spinner = ui.spinner(size='lg').props('color=primary')
                        ui.timer(0.1, lambda: spinner.set_visibility(True), once=True)

                        def task():
                            create_playlist(fetch_playlist_items(playlist_id), token, playlist_name, playlist_id)
                            spinner.set_visibility(False)
                            ui.notify('✅ Playlist fetched and added successfully!')
                            refresh_playlists()
                            render_dashboard()
                            playlist_id_input.value = ''
                            playlist_title_label.text = ''
                            fetch_button.disable()
                            playlist_verified['status'] = False

                        ui.timer(0.2, task, once=True)

                    playlist_id_input = ui.input('YouTube Playlist ID', on_change=on_input_change).classes('w-full')
                    playlist_title_label = ui.label('').classes('text-sm text-gray-600 mt-1')

                    with ui.row().classes('justify-start gap-3 mt-2'):
                        ui.button('Verify Playlist',
                                  on_click=caught_john_doe if not username else verify_playlist)
                        fetch_button = ui.button('Fetch Videos',
                                                 on_click=lambda: fetch_playlist_videos(playlist_id_input.value, user_token))
                        fetch_button.disable()

                # === Section: My Teams ===
                ui.label(f"👥 {user['name']}'s Teams").classes('text-lg font-bold mb-2')

                teams_column = ui.column().classes('gap-4 w-full')

                def refresh_teams():
                    teams_column.clear()

                    if not username:
                        both = fetch_teams_for_user_jd(44)
                    else:
                        both = fetch_teams_for_user(user_id)

                    owned, member = both["owned"], both["member"]
                    owned_ids = {t["_id"] for t in owned}
                    all_teams = owned + [t for t in member if t["_id"] not in owned_ids]

                    # -- Create Team Card --
                    with ui.column().classes('w-full p-4 border border-gray-300 rounded-lg bg-white shadow-md gap-3'):
                        with ui.row().classes('w-full justify-between items-center'):
                            ui.label('🛠 Create New Team').classes('text-lg font-bold')

                        team_name_input = ui.input('Team Name').props('outlined dense').classes('w-full mt-2')

                        def create_new_team():
                            name = team_name_input.value.strip()
                            if not name:
                                ui.notify('Please enter a team name.', type='warning')
                                return

                            create_team(name, user_token, user_id)
                            ui.notify(f'Team "{name}" created successfully!')
                            refresh_teams()
                            team_name_input.value = ''

                        ui.button(
                            'Create Team',
                            on_click=caught_john_doe if not username else create_new_team
                        ).props('color=primary').classes('mt-2 self-end')

                    for team in all_teams:
                        with teams_column:
                            with ui.column().classes('w-full p-4 border border-gray-300 rounded-lg bg-white shadow-md gap-2'):
                                with ui.row().classes('w-full justify-between items-center'):
                                    ui.label(team['name']).tooltip(team['_id']).classes('text-lg font-bold')
                                    if team['_id'] in owned_ids:
                                        with ui.row().classes('gap-2'):
                                            ui.button('Add User', on_click=lambda t=team: open_add_user_modal(t))
                                            ui.button('Add Playlist', on_click=lambda t=team: open_add_playlist_modal(t))
                                            ui.button('View Team', on_click=lambda t=team: open_team_modal(t))
                                    else:
                                        ui.label('👤 Member').classes('text-sm italic text-gray-500')

                                # Stub counts
                                ui.label(f"👥 Members: {len(team.get('member_ids', []))} | 🎵 Playlists: {team.get('playlist_count', 0)}").classes('text-sm text-gray-600')

                refresh_teams()

        # --- Right Main Panel ---
        with splitter.after:

            with ui.column().classes('w-full') as dashboard_column:

                def render_dashboard():
                    # Clear the column but keep the label intact
                    dashboard_column.clear()

                    videos = load_videos()
                    if not videos:
                        with dashboard_column:
                            with ui.card().classes('p-4 text-center'):
                                ui.label('⚠️ No videos found! Start by adding a playlist above.').classes('text-md')
                        return

                    dates = [datetime.datetime.strptime(v['date'], "%Y-%m-%dT%H:%M:%SZ") for v in videos]
                    # total_videos = len(videos)
                    # unique_partners = len(set(p for v in videos for p in v['partners']))
                    # unique_positions = len(set(p for v in videos for p in v['positions']))

                    with dashboard_column:
                        # with ui.row().classes('w-full gap-4'):
                        #     with ui.card().classes('p-4').tight():
                        #         ui.label(f"📹 Total Films: {total_videos}").classes('text-lg')
                        #     with ui.card().classes('p-4').tight():
                        #         ui.label(f"🧑‍🤝‍🧑 Training Partners: {unique_partners}").classes('text-lg')
                        #     with ui.card().classes('p-4').tight():
                        #         ui.label(f"📍 Unique Positions: {unique_positions}").classes('text-lg')
                        # ui.separator().classes('my-4 w-full')

                        calendar_container(grouped_videos_by_day)

                        ui.separator().classes('my-4 w-full')
                        date_counts = Counter(d.date() for d in dates)
                        sorted_dates = sorted(date_counts.keys())
                        chart_data = {
                            'labels': [d.strftime('%b %d, %Y') for d in sorted_dates],  # Human-readable date format
                            'datasets': [{
                                'label': 'Video Count',
                                'data': [date_counts[d] for d in sorted_dates],
                                'type': 'bar',
                                'itemStyle': {'color': '#4CAF50'},  # Custom bar color
                            }]
                        }

                        ui.echart({
                            'title': {
                                'text': 'Activity Over Time',
                                'left': 'center',
                                'textStyle': {'fontSize': 18, 'fontWeight': 'bold'},
                            },
                            'tooltip': {
                                'trigger': 'axis',
                                'axisPointer': {'type': 'shadow'},  # Highlight bar on hover
                                'formatter': '{b}: {c} videos',  # Custom tooltip format
                            },
                            'grid': {
                                'left': '10%',
                                'right': '10%',
                                'bottom': '15%',
                                'containLabel': True,  # Ensure labels fit within the chart
                            },
                            'xAxis': {
                                'type': 'category',
                                'data': chart_data['labels'],
                                'axisLabel': {
                                    'rotate': 45,  # Rotate labels for better readability
                                    'fontSize': 12,
                                },
                                'axisLine': {'lineStyle': {'color': '#888'}},  # Style the axis line
                            },
                            'yAxis': {
                                'type': 'value',
                                'axisLabel': {
                                    'fontSize': 12,
                                    'formatter': '{value}',  # Format y-axis values
                                },
                                'axisLine': {'lineStyle': {'color': '#888'}},  # Style the axis line
                                'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#ddd'}},  # Dashed grid lines
                            },
                            'series': [{
                                'type': 'bar',
                                'data': chart_data['datasets'][0]['data'],
                                'barWidth': '50%',  # Adjust bar width
                            }]
                        }).classes('w-full h-80')

                render_dashboard()

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
                "member_ids": ["user2", "user3", "user3"]
            }
        ],
        "member": [
            {
                "_id": "team2",
                "name": "Mao Pelo Pe",
                "playlist_count": 5,
                "owner_id": "another_user",
                "member_ids": [user_id, "user4", "user22", "user31", "user222", "user34", "user31", "user222", "user34", "user12", "user31", "user2", "user3", "user4"]
            }
        ]
    }

def open_add_user_modal(team):
    with ui.dialog() as dialog, ui.card().classes('w-[30rem]'):
        ui.label(f'➕ Add user to {team["name"]}').classes('text-lg font-semibold')

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

        with ui.row().classes('gap-2 mt-3'):
            ui.button('Add User', on_click=add_user).props('color=primary')
            ui.button('Cancel', on_click=dialog.close).props('flat')

    dialog.open()


def open_add_playlist_modal(team):
    with ui.dialog() as dialog, ui.card().classes('w-[30rem]'):
        ui.label(f'🎵 Add playlist to {team["name"]}').classes('text-lg font-semibold')

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

        with ui.row().classes('gap-2 mt-3'):
            ui.button('Add Playlist', on_click=add_playlist).props('color=primary')
            ui.button('Cancel', on_click=dialog.close).props('flat')

    dialog.open()

def open_team_modal(team):
    with ui.dialog() as dialog, ui.card().classes('w-[40rem]'):
        ui.label(f"👥 Team: {team['name']}").classes('text-lg font-semibold')

        members = [
            {"name": "Alice", "email": "alice@example.com", "role": "member", "joined": "2024-01-10"},
            {"name": "Bob", "email": "bob@example.com", "role": "member", "joined": "2024-02-12"},
        ]

        member_container = ui.column().classes('gap-2 mt-2')

        def refresh():
            member_container.clear()
            for member in members:
                with member_container:
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label(f"{member['name']} ({member['email']}) - {member['role']}, joined: {member['joined']}")
                        ui.button('Remove', on_click=lambda m=member: remove_member(m)).props('flat dense').classes('text-red-500')

        def remove_member(member):
            members.remove(member)
            ui.notify(f'Removed {member["name"]}')
            refresh()

        refresh()

        ui.button('Close', on_click=dialog.close).classes('mt-4')

    dialog.open()

def sync_playlist(playlist_id, token, playlist_name, play_id):
    try:
        # Step 1: Fetch existing videos from DB
        existing_videos = load_videos(playlist_id)
        if existing_videos:
            latest_saved_date_str = max(video["date"] for video in existing_videos)
            latest_saved_date = datetime.datetime.fromisoformat(latest_saved_date_str.replace("Z", "+00:00"))
            existing_video_ids = {video["video_id"] for video in existing_videos}
        else:
            latest_saved_date = None
            existing_video_ids = set()

        # Step 2: Fetch only new videos from YouTube
        latest_video_data = fetch_playlist_items(play_id, latest_saved_date)
        new_video_data = [video for video in latest_video_data if video["video_id"] not in existing_video_ids]

        if not new_video_data:
            ui.notify('✅ Playlist is already up to date!')
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

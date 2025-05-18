from nicegui import ui, app
from dialog_puns import caught_john_doe, in_progress
from fetch_videos import fetch_playlist_items, fetch_playlist_metadata
from utils_api import create_video, load_playlists, load_videos, create_playlist, load_playlists_for_user, create_team, fetch_teams_for_user
import datetime
from collections import Counter


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

    ui.label(f"Welcome, {user['name']}").classes('text-2xl font-bold mb-4')
    with ui.splitter(value=30).classes('w-full h-auto gap-4 mt-2') as splitter:

        # --- Left Side Panel ---
        with splitter.before:
            with ui.column().classes('w-full h-full p-6 gap-6 bg-gray-100 rounded-xl shadow-md'):
                
                # === Section: YouTube Playlists ===
                ui.label('🎵 My YouTube Playlists').classes('text-xl font-bold')

                playlists_column = ui.column().classes('gap-2')

                def refresh_playlists():
                    playlists_column.clear()

                    if not username:
                        playlists = load_playlists()
                        for playlist in playlists:
                            with playlists_column:
                                with ui.row().classes('justify-between items-center w-full'):
                                    ui.label(playlist['name']).tooltip(playlist['_id'])
                                    ui.button('Sync', on_click=lambda: caught_john_doe())
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
                                with ui.row().classes('justify-between items-center w-full'):
                                    ui.label(playlist['name']).tooltip(playlist['_id'])
                                    if playlist['_id'] in owned_ids:
                                        ui.button('Sync', on_click=lambda pid=playlist['_id'], name=playlist['name'], play_id=playlist['playlist_id']: on_sync_click(pid, user_token, name, play_id))

                refresh_playlists()
                ui.separator().classes('my-4')
##
                # === Section: Add Playlist by ID ===
                ui.label('➕ Add Playlist by ID').classes('text-lg font-semibold')

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
                playlist_title_label = ui.label('')

                with ui.row().classes('justify-start gap-3'):
                    verify_btn = ui.button('Verify Playlist',
                                        on_click=caught_john_doe if not username else verify_playlist)
                    fetch_button = ui.button('Fetch Videos',
                                            on_click=lambda: fetch_playlist_videos(playlist_id_input.value, user_token))
                    fetch_button.disable()

                ui.separator().classes('my-4')

                # === Section: My Teams ===
                ui.label('👥 My Teams').classes('text-xl font-bold')

                teams_column = ui.column().classes('gap-2')

                def refresh_teams():
                    teams_column.clear()

                    if not username:
                        both = fetch_teams_for_user_jd(44)
                    else:
                        both = fetch_teams_for_user(user_id)

                    owned, member = both["owned"], both["member"]
                    owned_ids = {t["_id"] for t in owned}
                    all_teams = owned + [t for t in member if t["_id"] not in owned_ids]

                    for team in all_teams:
                        with teams_column:
                            with ui.row().classes('justify-between items-center w-full'):
                                ui.label(team['name']).tooltip(team['_id'])
                                if team['_id'] in owned_ids:
                                    with ui.row().classes('gap-2'):
                                        ui.button('Add User', on_click=lambda t=team: open_add_user_modal(t))
                                        ui.button('Add Playlist', on_click=lambda t=team: open_add_playlist_modal(t))
                                else:
                                    ui.label('Member').classes('text-sm text-gray-500 italic')

                refresh_teams()
                ui.separator().classes('my-4')

                # === Section: Create New Team ===
                ui.label('🛠 Create New Team').classes('text-lg font-semibold')

                team_name_input = ui.input('Team Name').classes('w-full')

                def create_new_team():
                    name = team_name_input.value.strip()
                    if not name:
                        ui.notify('Please enter a team name.', type='warning')
                        return

                    create_team(name, user_token)
                    ui.notify(f'Team "{name}" created successfully!')
                    refresh_teams()
                    team_name_input.value = ''

                ui.button('Create Team',
                        on_click=caught_john_doe if not username else create_new_team).classes('mt-2')

        # --- Right Main Panel ---
        with splitter.after:
            with ui.column().classes('p-4 m-2 gap-4') as dashboard_column:
                ui.label("🤼 Grappling Portfolio Dashboard").classes('text-2xl font-bold mt-8 mb-4')
                
            def render_dashboard():
                dashboard_column.clear()

                videos = load_videos()
                if not videos:
                    with dashboard_column:
                        with ui.card().classes('p-4 text-center'):
                            ui.label('⚠️ No videos found! Start by adding a playlist above.').classes('text-md')
                    return

                dates = [datetime.datetime.strptime(v['date'], "%Y-%m-%dT%H:%M:%SZ") for v in videos]
                total_videos = len(videos)
                unique_partners = len(set(p for v in videos for p in v['partners']))
                unique_positions = len(set(p for v in videos for p in v['positions']))

                with dashboard_column:
                    with ui.row().classes('w-full gap-4'):
                        with ui.card().classes('p-4').tight():
                            ui.label(f"📹 Total Videos: {total_videos}").classes('text-lg')
                        with ui.card().classes('p-4').tight():
                            ui.label(f"🧑‍🤝‍🧑 Training Partners: {unique_partners}").classes('text-lg')
                        with ui.card().classes('p-4').tight():
                            ui.label(f"📍 Unique Positions: {unique_positions}").classes('text-lg')

                    ui.label("📊 Activity Over Time").classes('text-xl mt-8 mb-2')
                    date_counts = Counter(d.date() for d in dates)
                    sorted_dates = sorted(date_counts.keys())
                    chart_data = {
                        'labels': [d.strftime('%Y-%m-%d') for d in sorted_dates],
                        'datasets': [{
                            'label': 'Video count',
                            'data': [date_counts[d] for d in sorted_dates],
                        }]
                    }
                    ui.echart({
                        'title': {'left': 'center'},
                        'tooltip': {'trigger': 'axis'},
                        'xAxis': {'type': 'category', 'data': chart_data['labels']},
                        'yAxis': {'type': 'value'},
                        'series': [{
                            'type': 'bar',
                            'data': chart_data['datasets'][0]['data'],
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
                "name": "Core Team",
                "owner_id": user_id,
                "member_ids": ["user2", "user3"]
            }
        ],
        "member": [
            {
                "_id": "team2",
                "name": "Collab Team",
                "owner_id": "another_user",
                "member_ids": [user_id, "user4"]
            }
        ]
    }

def open_add_user_modal(team):
    with ui.dialog() as dialog, ui.card():
        ui.label(f'Add user to team: {team["name"]}').classes('font-semibold')
        email_input = ui.input('User Email')

        def add_user():
            email = email_input.value.strip()
            if not email:
                ui.notify("Enter a valid email.", type="warning")
                return
            # Simulate backend add logic
            print(f"Adding user with email '{email}' to team '{team['_id']}'")
            ui.notify(f"✅ Added {email} to {team['name']}")
            dialog.close()

        ui.button('Add User', on_click=add_user)
        ui.button('Cancel', on_click=dialog.close)

    dialog.open()

def open_add_playlist_modal(team):
    with ui.dialog() as dialog, ui.card():
        ui.label(f'Add Playlist to team: {team["name"]}').classes('font-semibold')
        playlist_id_input = ui.input('Playlist ID')

        def add_playlist():
            pid = playlist_id_input.value.strip()
            if not pid:
                ui.notify("Enter a valid Playlist ID.", type="warning")
                return
            # Simulate backend logic
            print(f"Adding playlist '{pid}' to team '{team['_id']}'")
            ui.notify(f"✅ Added playlist to {team['name']}")
            dialog.close()

        ui.button('Add Playlist', on_click=add_playlist)
        ui.button('Cancel', on_click=dialog.close)

    dialog.open()

def sync_playlist(playlist_id, token, playlist_name, play_id):

    try:
        # Step 1: Fetch current playlist data from source (YouTube, etc.)
        latest_video_data = fetch_playlist_items(play_id)
        latest_video_ids = {video['video_id'] for video in latest_video_data}

        # Step 2: Fetch existing videos in DB for this playlist
        existing_videos = load_videos(playlist_id)
        existing_video_ids = {video['video_id'] for video in existing_videos}

        # Step 3: Identify new videos
        new_video_data = [video for video in latest_video_data if video['video_id'] not in existing_video_ids]
        if not new_video_data:
            ui.notify('✅ Playlist is already up to date!')
            return

        # Step 4: Append new videos
        create_video(new_video_data, token, playlist_name)
        ui.notify(f'✅ Synced {len(new_video_data)} new videos to "{playlist_name}".')

    except Exception as exc:
        ui.notify(f'❌ Sync failed: {str(exc)}')


def create_team_modal():
    print("Opening modal to create a new team")

def open_team_modal(team):
    print(f"Opening team: {team['name']}")

def view_playlist_videos(playlist):
    print(f"Viewing videos for playlist: {playlist['title']}")

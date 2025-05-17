from nicegui import ui, app
from dialog_puns import caught_john_doe, in_progress
from fetch_videos import fetch_playlist_items, fetch_playlist_metadata
from utils_api import load_playlists, load_videos, create_playlist
import datetime
from collections import Counter


@ui.page('/home')
def home_page():
    username = app.storage.user.get("user", None)
    user_token = app.storage.user.get("token", None)
    user_id = app.storage.user.get("id", None)
    if not username:
        user = {"id": 1, "name": "John Doe"}
    else:
        user = {"id": 1, "name": username}

    if not user:
        ui.label('You must be logged in to view this page.')
        return

    ui.label(f"Welcome, {user['name']}").classes('text-2xl font-bold mb-4')

    with ui.splitter(value=30).classes('w-full h-auto gap-4 mt-2') as splitter:
        with splitter.before:
            with ui.column().classes('w-full h-full p-4 m-2 gap-4 bg-gray-100 rounded-xl shadow-md'):
                ui.label('My YouTube Playlists').classes('font-semibold mb-2')
                playlists_column = ui.column()

                def refresh_playlists():
                    playlists_column.clear()
                    playlists = load_playlists()
                    for playlist in playlists:
                        with playlists_column:
                            with ui.row().classes('items-center justify-between w-full'):
                                ui.label(playlist['name']).tooltip(playlist['_id'])
                                if not username:
                                    ui.button('Sync', on_click=lambda: caught_john_doe())
                                else:
                                    ui.button('Sync', on_click=lambda: in_progress())
                                    # ui.button('Sync', on_click=lambda name=playlist['name']: sync_playlist(name))

                refresh_playlists()

                ui.separator()
                ui.label('Add Playlist by ID').classes('font-semibold mt-4')

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
                        create_playlist(fetch_playlist_items(playlist_id), token, playlist_name)
                        spinner.set_visibility(False)
                        ui.notify('✅ Playlist fetched and added successfully!')
                        refresh_playlists()
                        render_dashboard()  # <== Refresh dashboard right after fetching
                        # Reset for next entry
                        playlist_id_input.value = ''
                        playlist_title_label.text = ''
                        fetch_button.disable()
                        playlist_verified['status'] = False


                    ui.timer(0.2, task, once=True)

                playlist_id_input = ui.input('YouTube Playlist ID', on_change=on_input_change)
                playlist_title_label = ui.label('')

                with ui.row().classes('items-center justify-between w-full'):
                    if not username:
                        ui.button('Verify Playlist', on_click=caught_john_doe)
                    else:
                        ui.button('Verify Playlist', on_click=verify_playlist)
                    fetch_button = ui.button('Fetch Videos', on_click=lambda: fetch_playlist_videos(playlist_id_input.value, user_token))
                    fetch_button.disable()

                ui.separator()
                ui.label('Teams').classes('font-semibold mt-4')
                teams = []  # Replace with: fetch_teams_for_user(user['id'])
                for team in teams:
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label(team['name'])
                        ui.button('Manage', on_click=lambda t=team: open_team_modal(t))

                if not username:
                    ui.button('Create New Team', on_click=lambda: caught_john_doe())
                else:
                    ui.button('Create New Team', on_click=lambda: create_team_modal())

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
def sync_playlist(playlist_id):
    print(f"Syncing playlist {playlist_id}...")

def create_team_modal():
    print("Opening modal to create a new team")

def fetch_playlist_info(playlist_id):
    print("Opening fetch_playlist_info")

def open_team_modal(team):
    print(f"Opening team: {team['name']}")

def view_playlist_videos(playlist):
    print(f"Viewing videos for playlist: {playlist['title']}")

# with ui.column().classes('w-full h-full p-4 m-2 gap-4 bg-gray-100 rounded-xl shadow-md'):
#     with ui.tabs().classes('w-full') as tabs:
#         playlist_tab = ui.tab('Playlists')
#         team_tab = ui.tab('Teams')

#     # with ui.tabs().classes('w-full') as tabs:
#     #     playlist_tab = ui.tab('Playlists')
#     #     team_tab = ui.tab('Teams')

#     with ui.tab_panels(tabs, value='Playlists').classes('w-full'):
#         with ui.tab_panel('Playlists'):
#             ui.label('Your Synced Playlists').classes('text-xl font-semibold mb-2')
#             for playlist in playlists:
#                 with ui.card().classes('mb-4 shadow-md p-4'):
#                     ui.label(playlist['name']).classes('text-lg font-bold')
#                     ui.label(f"{len(playlist.get('videos', []))} videos")
#                     ui.button('View', on_click=lambda p=playlist: view_playlist_videos(p))

#         with ui.tab_panel('Teams'):
#             ui.label('Your Teams').classes('text-xl font-semibold mb-2')
#             for team in teams:
#                 with ui.card().classes('mb-4 shadow-md p-4'):
#                     ui.label(team['name']).classes('text-lg font-bold')
#                     ui.label(f"Members: {len(team.get('members', []))}")
#                     ui.label(f"Playlists: {len(team.get('playlists', []))}")
#                     ui.button('Manage Team', on_click=lambda t=team: open_team_modal(t))

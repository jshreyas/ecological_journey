from nicegui import ui
from john_doe import caught_john_doe
from utils_api import load_playlists, load_videos
import datetime
from collections import Counter


@ui.page('/home')
def home_page():
    user = {"id": 1, "name": "John Doe"}
    if not user:
        ui.label('You must be logged in to view this page.')
        return

    ui.label(f"Welcome, {user['name']}").classes('text-2xl font-bold mb-4')

    with ui.splitter(value=30).classes('w-full h-auto gap-4 mt-2') as splitter:
        with splitter.before:
            with ui.column().classes('w-full h-full p-4 m-2 gap-4 bg-gray-100 rounded-xl shadow-md'):
                ui.label('My Playlists').classes('font-semibold mb-2')
                playlists = load_playlists()

                for playlist in playlists:
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label(playlist['name']).tooltip(playlist['_id'])
                        ui.button('Sync', on_click=lambda: caught_john_doe())

                ui.separator()
                ui.label('Add Playlist by ID').classes('font-semibold mt-4')
                playlist_id_input = ui.input(placeholder='YouTube Playlist ID')
                ui.button('Fetch', on_click=lambda: caught_john_doe())

                ui.separator()
                ui.label('Teams').classes('font-semibold mt-4')
                teams = []  # Replace with: fetch_teams_for_user(user['id'])
                for team in teams:
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label(team['name'])
                        ui.button('Manage', on_click=lambda t=team: open_team_modal(t))

                ui.button('Create New Team', on_click=lambda: caught_john_doe()).classes('mt-4')

        # --- Right Main Panel ---
        with splitter.after:
            with ui.column().classes('p-4 m-2 gap-4'):
                # --- Grappling Portfolio Dashboard ---
                ui.label("🤼 Grappling Portfolio Dashboard").classes('text-2xl font-bold mt-8 mb-4')

                videos = load_videos()
                if not videos:
                    ui.notify('⚠️ No videos found!')
                    return

                # Data Processing
                dates = [datetime.datetime.strptime(v['date'], "%Y-%m-%dT%H:%M:%SZ") for v in videos]
                total_videos = len(videos)
                unique_partners = len(set(p for v in videos for p in v['partners']))
                unique_positions = len(set(p for v in videos for p in v['positions']))

                # Stats
                with ui.row().classes('w-full gap-4'):
                    with ui.card().classes('p-4').tight():
                        ui.label(f"📹 Total Videos: {total_videos}").classes('text-lg')
                    with ui.card().classes('p-4').tight():
                        ui.label(f"🧑‍🤝‍🧑 Training Partners: {unique_partners}").classes('text-lg')
                    with ui.card().classes('p-4').tight():
                        ui.label(f"📍 Unique Positions: {unique_positions}").classes('text-lg')

                # Chart: Activity Over Time
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


# --- Stubbed Actions ---
def sync_playlist(playlist_id):
    print(f"Syncing playlist {playlist_id}...")


def fetch_playlist_by_id(playlist_id):
    print(f"Fetching playlist with ID: {playlist_id}")


def create_team_modal():
    print("Opening modal to create a new team")


def open_team_modal(team):
    print(f"Opening team: {team['name']}")


def view_playlist_videos(playlist):
    print(f"Viewing videos for playlist: {playlist['title']}")

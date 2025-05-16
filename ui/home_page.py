from nicegui import ui
# from utils.auth import get_current_user
from utils_api import load_playlists
from nicegui import ui
import random


@ui.page('/home')
def home_page():
    user = {"id": 1, "name": "John Doe"}
    if not user:
        ui.label('You must be logged in to view this page.')
        return

    ui.label(f"Welcome, {user['name']}").classes('text-2xl font-bold mb-4')

 
    JOHN_DOE_PUNS = [
        lambda: create_dialog(
            title="🎭 Caught you, John Doe!",
            body="Click responsibly... or face more dad jokes.",
            button_text="Dismiss"
        ),
        lambda: create_dialog(
            title="🎉 John Doe Detected!",
            body="Trying to sneak a click, huh?\n\nDemo mode is safe for browsing but locked for edits.",
            button_text="I’ll behave"
        ),
        # lambda: ui.notify("🕵️‍♂️ Caught John Doe red-handed! No edits for you.", type='warning', duration=5000),
        # lambda: ui.notify("Nice try, demo king 🤡", type='warning'),
        # lambda: ui.notify("Caught in the act, Mr. Doe.", type='warning', duration=4000),
        # lambda: ui.notify("You just triggered our highly experimental anti-demo edit shield.", type='warning', duration=4000),
        # lambda: ui.notify("John Doe detected... deploying sarcasm mode.", type='warning', duration=4000),
        # lambda: ui.notify("Even Capoeira needs rules. Demo users don’t get to *ginga* all over the DB.", type='warning', duration=5000),
    ]

    def create_dialog(title: str, body: str, button_text: str):
        with ui.dialog() as d:
            with ui.card().classes("bg-yellow-50 shadow-md"):
                ui.label(title).classes("text-lg font-bold")
                ui.markdown(body)
                ui.button(button_text).on("click", d.close)
        d.open()

    def caught_john_doe():
        random.choice(JOHN_DOE_PUNS)()

    def john_doe_button(*args, **kwargs):
        button = ui.button(*args, **kwargs)
        button.on("click", lambda: caught_john_doe())
        return button


    with ui.row().classes('w-full gap-8'):

        # --- Left Sidebar (Navigation / Quick Actions) ---
        with ui.column().classes('w-1/4 bg-gray-100 p-4 rounded-xl shadow-md'):
            ui.label('My Playlists').classes('font-semibold mb-2')
            playlists = load_playlists()

            for playlist in playlists:
                with ui.row().classes('items-center justify-between w-full'):
                    ui.label(playlist['name']).tooltip(playlist['_id'])
                    ui.button('Sync', on_click=lambda: caught_john_doe())

            ui.separator()
            ui.label('Add Playlist by ID').classes('font-semibold mt-4')
            playlist_id_input = ui.input(placeholder='YouTube Playlist ID')
            ui.button('Fetch', on_click=lambda: fetch_playlist_by_id(playlist_id_input.value))

            ui.separator()
            ui.label('Teams').classes('font-semibold mt-4')
            # teams = fetch_teams_for_user(user['id'])
            teams = []
            for team in teams:
                with ui.row().classes('items-center justify-between w-full'):
                    ui.label(team['name'])
                    ui.button('Manage', on_click=lambda t=team: open_team_modal(t))

            ui.button('Create New Team', on_click=create_team_modal).classes('mt-4')

        # --- Right Main Panel (Tabbed Content) ---
        with ui.column().classes('w-3/4'):
            with ui.tabs().classes('w-full') as tabs:
                playlist_tab = ui.tab('Playlists')
                team_tab = ui.tab('Teams')

            with ui.tab_panels(tabs, value=playlist_tab).classes('w-full'):

                with ui.tab_panel(playlist_tab):
                    ui.label('Your Synced Playlists').classes('text-xl font-semibold mb-2')
                    for playlist in playlists:
                        with ui.card().classes('mb-4 shadow-md p-4'):
                            ui.label(playlist['name']).classes('text-lg font-bold')
                            ui.label(f"{len(playlist.get('videos', []))} videos")
                            ui.button('View', on_click=lambda p=playlist: view_playlist_videos(p))

                with ui.tab_panel(team_tab):
                    ui.label('Your Teams').classes('text-xl font-semibold mb-2')
                    for team in teams:
                        with ui.card().classes('mb-4 shadow-md p-4'):
                            ui.label(team['name']).classes('text-lg font-bold')
                            ui.label(f"Members: {len(team.get('members', []))}")
                            ui.label(f"Playlists: {len(team.get('playlists', []))}")
                            ui.button('Manage Team', on_click=lambda t=team: open_team_modal(t))


# --- Stubs for actions ---
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

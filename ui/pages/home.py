from nicegui import ui

from ui.log import log
from ui.pages.components.home.calendar_tab import CalendarTab
from ui.pages.components.home.feed_tab import FeedTab
from ui.pages.components.home.playlist_tab import PlaylistTab
from ui.pages.components.home.state import State
from ui.utils.dialog_puns import caught_john_doe
from ui.utils.user_context import User, with_user_context
from ui.utils.utils_api import create_team, fetch_teams_for_user


@with_user_context
def home_page(user: User | None):

    home_state = State(user)
    calendar_tab = CalendarTab(home_state)
    feed_tab = FeedTab(home_state)
    playlist_tab = PlaylistTab(home_state)

    with ui.splitter(value=50).classes("w-full h-[600px] gap-4") as splitter:
        with splitter.before:
            with ui.tabs().classes("w-full") as tabs:
                tab_playlists = ui.tab("🎵 Playlists")
                tab_teams = ui.tab("👥 Teams")
                tab_calendar = ui.tab("📅 Calendar")
            with ui.tab_panels(tabs, value=tab_calendar).classes("w-full h-full"):
                with ui.tab_panel(tab_playlists) as playlists_container:
                    playlist_tab.create_tab(playlists_container)
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
                with ui.tab_panel(tab_calendar).classes("w-full h-full p-0") as calendar_container:
                    calendar_tab.create_tab(calendar_container)

        with splitter.after:
            with ui.column().classes("w-full h-full") as dashboard_column:
                feed_tab.create_tab(dashboard_column)


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


def create_team_modal():
    log.info("Opening modal to create a new team")


def view_playlist_videos(playlist):
    log.info(f"Viewing videos for playlist: {playlist['title']}")

from nicegui import ui

from ui.pages.components.home.calendar_tab import CalendarTab
from ui.pages.components.home.feed_tab import FeedTab
from ui.pages.components.home.playlist_tab import PlaylistTab
from ui.pages.components.home.state import State
from ui.pages.components.home.team_tab import TeamTab
from ui.utils.user_context import User, with_user_context


@with_user_context
def home_page(user: User | None):

    home_state = State(user)
    calendar_tab = CalendarTab(home_state)
    feed_tab = FeedTab(home_state)
    playlist_tab = PlaylistTab(home_state)
    team_tab = TeamTab(home_state)

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
                    team_tab.create_tab(teams_container)
                with ui.tab_panel(tab_calendar).classes("w-full h-full p-0") as calendar_container:
                    calendar_tab.create_tab(calendar_container)

        with splitter.after:
            with ui.column().classes("w-full h-full") as feed_container:
                feed_tab.create_tab(feed_container)

import calendar
from collections import Counter
from datetime import date, datetime

from nicegui import ui

from ui.data.crud import load_playlists
from ui.utils.user_context import User, with_user_context
from ui.utils.utils import group_videos_by_day
from ui.utils.utils_api import create_playlist, fetch_teams_for_user, load_playlists_for_user, load_videos
from ui.utils.youtube import fetch_playlist_metadata

# ============================================================
# HOME STATE
# ============================================================


class HomeState:

    def __init__(self, user: User | None):
        self.user = user
        self.user_id = user.id if user else None
        self.token = user.token if user else None

        self.playlists = []
        self.teams = []
        self.videos = []

    def load_playlists(self):
        if not self.user:
            self.playlists = load_playlists()
        else:
            both = load_playlists_for_user(self.user_id)
            owned, member = both["owned"], both["member"]
            owned_ids = {pl["_id"] for pl in owned}
            self.playlists = owned + [p for p in member if p["_id"] not in owned_ids]

    def load_teams(self):
        if not self.user:
            return {"owned": [], "member": []}
        return fetch_teams_for_user(self.user_id)

    def load_videos(self):
        self.videos = load_videos()
        return self.videos


# ============================================================
# CALENDAR STATE
# ============================================================


class CalendarState:

    def __init__(self, grouped_videos_by_day: dict):
        self.grouped = grouped_videos_by_day
        self.current_month = date.today().replace(day=1)

    def change_month(self, offset: int):
        month = self.current_month.month + offset
        year = self.current_month.year

        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1

        self.current_month = date(year, month, 1)


@with_user_context
def home_page(user: User | None):
    state = HomeState(user)
    HomeLayout(state).build()


class HomeLayout:

    def __init__(self, state: HomeState):
        self.state = state

    def build(self):

        with ui.splitter(value=25).classes("w-full h-[600px] gap-4") as splitter:

            with splitter.before:
                with ui.tabs().classes("w-full") as tabs:
                    tab_playlists = ui.tab("🎵 Playlists")
                    tab_teams = ui.tab("👥 Teams")

                with ui.tab_panels(tabs, value=tab_playlists):

                    with ui.tab_panel(tab_playlists) as playlists_container:
                        dashboard_component = DashboardComponent(self.state)
                        PlaylistComponent(self.state, dashboard_component).build(playlists_container)

                    with ui.tab_panel(tab_teams) as teams_container:
                        TeamComponent(self.state).build(teams_container)

            with splitter.after:
                with ui.column().classes("w-full") as dashboard_column:
                    DashboardComponent(self.state).build(dashboard_column)


class TeamComponent:

    def __init__(self, state: HomeState):
        self.state = state

    def build(self, parent):
        parent.clear()

        teams = self.state.load_teams()
        owned, member = teams["owned"], teams["member"]
        owned_ids = {t["_id"] for t in owned}
        all_teams = owned + [t for t in member if t["_id"] not in owned_ids]

        for team in all_teams:
            with parent:
                with ui.card().classes("w-full p-3 border rounded shadow"):
                    ui.label(team["name"]).classes("font-semibold")
                    ui.label(f"👥 {len(team.get('member_ids', []))}")


class DashboardComponent:

    def __init__(self, state: HomeState):
        self.state = state

    def build(self, parent):
        parent.clear()

        videos = self.state.load_videos()
        if not videos:
            with parent:
                with ui.card().classes("p-4 text-center"):
                    ui.label("⚠️ No videos found! Start by adding a playlist.")
            return

        grouped = group_videos_by_day(videos)

        with parent:
            CalendarComponent(CalendarState(grouped)).build()

            ui.separator().classes("my-4 w-full")

            self._render_chart(videos)

    def _render_chart(self, videos):
        dates = [datetime.strptime(v["date"], "%Y-%m-%dT%H:%M:%SZ") for v in videos]
        date_counts = Counter(d.date() for d in dates)
        sorted_dates = sorted(date_counts.keys())

        ui.echart(
            {
                "title": {"text": "Activity Over Time", "left": "center"},
                "xAxis": {"type": "category", "data": [d.strftime("%b %d, %Y") for d in sorted_dates]},
                "yAxis": {"type": "value"},
                "series": [
                    {
                        "type": "bar",
                        "data": [date_counts[d] for d in sorted_dates],
                    }
                ],
            }
        ).classes("w-full h-80")


class PlaylistComponent:

    def __init__(self, state: HomeState, dashboard: DashboardComponent):
        self.state = state
        self.dashboard = dashboard

    def build(self, parent):
        parent.clear()
        self.state.load_playlists()

        for playlist in self.state.playlists:
            with parent:
                with ui.card().classes("w-full p-3 border rounded shadow"):
                    ui.label(playlist["name"]).classes("font-semibold")

        self._add_playlist_card(parent)

    def _add_playlist_card(self, parent):
        with parent:
            with ui.card().classes("w-full p-4 border rounded shadow"):
                ui.label("➕ Playlist by ID")

                playlist_input = ui.input("YouTube Playlist ID").classes("w-full")

                async def create():
                    pid = playlist_input.value.strip()
                    if not pid:
                        ui.notify("Enter Playlist ID")
                        return
                    metadata = await fetch_playlist_metadata(pid)
                    if not metadata:
                        ui.notify("Invalid Playlist")
                        return
                    create_playlist([], self.state.token, metadata["title"], pid)
                    ui.notify("Playlist Created")
                    self.build(parent)
                    self.dashboard.build(parent.parent)

                ui.button("Create", on_click=create)


class CalendarComponent:

    def __init__(self, state: CalendarState):
        self.state = state
        self.month_label = None
        self.grid = None

    def build(self):

        with ui.column().classes("w-full h-full items-center"):

            with ui.row().classes("w-full justify-between items-center"):
                ui.button("← Previous", on_click=lambda: self._change(-1)).props("flat")
                self.month_label = ui.label("").classes("text-xl font-bold")
                ui.button("Next →", on_click=lambda: self._change(1)).props("flat")

            with ui.row().classes("w-full h-full max-w-5xl flex-1 bg-white rounded-lg shadow-lg overflow-hidden"):
                with ui.column().classes("w-full h-full gap-2"):
                    self.grid = ui.grid(columns=7).classes("gap-2 w-full h-full")
                    self.render()

    def render(self):
        self.grid.clear()

        year = self.state.current_month.year
        month = self.state.current_month.month
        first_day = date(year, month, 1)

        self.month_label.text = first_day.strftime("%B %Y")

        start_weekday = first_day.weekday()
        days_in_month = calendar.monthrange(year, month)[1]

        with self.grid:
            for wd in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
                ui.label(wd).classes("text-center font-semibold text-gray-600")

            for _ in range(start_weekday):
                ui.label("")

            for day in range(1, days_in_month + 1):
                d = date(year, month, day)
                d_str = d.strftime("%Y-%m-%d")
                videos = self.state.grouped.get(d_str, [])

                with ui.card().classes(
                    "h-20 p-2 bg-gray-50 border border-gray-300 shadow-sm hover:shadow-md rounded-lg"
                ):
                    with ui.row().classes("w-full justify-between"):
                        ui.label(str(day)).classes("text-sm font-bold")

                    if videos:
                        ui.link(f"{len(videos)} film(s)", f'/film/{videos[0]["video_id"]}').classes(
                            "text-xs no-underline"
                        )

    def _change(self, offset):
        self.state.change_month(offset)
        self.render()

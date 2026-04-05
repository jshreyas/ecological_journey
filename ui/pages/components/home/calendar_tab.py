from nicegui import events, ui

from ui.pages.components.home.fullcalendar import FullCalendar

from .state import State

# TODO: update this mapping in playlist color db, get rid of this
TAILWIND_TO_HEX = {
    "bg-red-400": "#f87171",
    "bg-blue-400": "#60a5fa",
    "bg-green-400": "#4ade80",
    "bg-yellow-400": "#facc15",
    "bg-purple-400": "#c084fc",
    "bg-pink-400": "#f472b6",
    "bg-teal-400": "#2dd4bf",
    "bg-indigo-400": "#818cf8",
    "bg-gray-400": "#9ca3af",
    "bg-orange-400": "#fb923c",
    "bg-[#ff00ff]": "#ff00ff",
    "bg-[#5c2e00]": "#5c2e00",
    "bg-[#ff99ff]": "#ff99ff",
    "bg-[#66ffff]": "#66ffff",
    "bg-[#ff8000]": "#ff8000",
}


def get_event_color(tw_class: str | None):
    if not tw_class:
        return "#888888"
    return TAILWIND_TO_HEX.get(tw_class, "#888888")


class CalendarTab:
    """Component for displaying calendar"""

    def __init__(self, home_state: State):
        self.home_state = home_state
        self.container = None

        self.home_state.add_refresh_callback(self.refresh)

    def create_tab(self, container):
        """Create the calendar tab UI"""
        self.container = container
        self.refresh()

    def refresh(self):
        """Refresh the calendar tab with current video data"""
        if not self.container:
            return

        self.container.clear()
        with self.container:
            self._create_calendar_ui()

    def build_calendar_events(self, videos: list[dict]) -> list[dict]:
        events = []

        for v in videos:
            start = v["date"].split("T")[0]  # Extract date part, ignore time
            events.append(
                {
                    "id": v["video_id"],  # 👈 CRITICAL for navigation
                    "title": "",
                    "start": start,
                    "allDay": False,
                    "backgroundColor": get_event_color(v.get("playlist_color")),
                    "borderColor": get_event_color(v.get("playlist_color")),
                }
            )
        return events

    def _create_calendar_ui(self):
        """Create the calendar UI"""

        options = {
            "initialView": "dayGridMonth",
            "headerToolbar": {"left": "prev,next today", "right": "title"},
            "allDaySlot": False,
            "timeZone": "local",
            "height": "auto",
            "width": "auto",
            "displayEventTime": False,
            "events": self.build_calendar_events(self.home_state.load_videos()),
        }

        def handle_click(event: events.GenericEventArguments):
            if "info" not in event.args:
                return

            event_data = event.args["info"]["event"]

            # 👇 choose navigation strategy
            video_id = event_data.get("id")
            date_str = event_data.get("start", "").split("T")[0]

            if video_id:
                anchor = self.home_state.get_video_anchor(video_id)
            else:
                anchor = self.home_state.get_date_anchor(date_str)

            ui.run_javascript(f"scrollToAnchor('{anchor}')")

        FullCalendar(options, on_click=handle_click)

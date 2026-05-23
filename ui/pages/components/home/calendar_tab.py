from nicegui import events, ui

from ui.pages.components.home.fullcalendar import FullCalendar

from .state import State


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
                    "backgroundColor": v.get("playlist_color"),
                    "borderColor": v.get("playlist_color"),
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

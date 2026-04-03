from ui.utils.user_context import User


class State:
    """Centralized state management for home page and refresh callbacks"""

    def __init__(self, user: User | None = None):
        self.user = user

    def get_date_anchor(self, date_str: str):
        return f"date-{date_str.split('T')[0]}"

    def get_video_anchor(self, video_id: str):
        return f"video-{video_id}"

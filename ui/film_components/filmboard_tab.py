"""
FilmboardTab - Component for displaying videos from the same day
Handles the filmboard functionality for showing related videos
"""
from nicegui import ui
from utils.utils_api import load_videos
from films import navigate_to_film
from .video_state import VideoState
from typing import Callable, Optional


class FilmboardTab:
    """Component for displaying videos from the same day"""
    
    def __init__(self, video_state: VideoState, on_video_select: Callable = None):
        self.video_state = video_state
        self.on_video_select = on_video_select
        self.container = None
        
        # Register for video state refresh notifications
        self.video_state.add_refresh_callback(self.refresh)
    
    def create_tab(self, container):
        """Create the filmboard tab UI"""
        self.container = container
        self.refresh()
    
    def refresh(self):
        """Refresh the filmboard tab with current video data"""
        if not self.container:
            return
            
        self.container.clear()
        with self.container:
            self._create_filmboard_ui()
    
    def _create_filmboard_ui(self):
        """Create the filmboard UI"""
        video = self.video_state.get_video()
        if not video:
            ui.label("No video data available")
            return
        
        current_video_date = video.get('date', '').split('T')[0]
        if not current_video_date:
            ui.label("No date information available")
            return
        
        # Get videos from the same day
        all_videos = load_videos()
        same_day_videos = [
            v for v in all_videos 
            if v['video_id'] != self.video_state.video_id 
            and v.get('date', '').split('T')[0] == current_video_date
        ]
        
        if not same_day_videos:
            ui.label("No other videos from the same day").classes('text-gray-500 text-center p-4')
            return
        
        # Display videos from the same day
        for video_data in same_day_videos:
            self._add_video_card(video_data)
    
    def _add_video_card(self, video_data):
        """Add a video card to the filmboard"""
        with ui.card().classes('w-full p-4 mb-2 cursor-pointer').on('click', lambda e: self._handle_video_click(video_data['video_id'], e)):
            # Header with title and duration
            with ui.row().classes('justify-between items-center'):
                ui.label(video_data.get('title', 'Untitled')).classes('font-semibold text-lg')
                ui.label(video_data.get('duration_human', 'Unknown')).classes('text-sm text-gray-600')
            
            # Video details
            with ui.row().classes('text-sm text-gray-600 mb-2'):
                clips_count = len(video_data.get('clips', []))
                ui.label(f"📹 {clips_count} clips")
                ui.label(f"📅 {video_data.get('playlist_name', 'Unknown playlist')}")
            
            # Partners and labels
            partners = video_data.get('partners', [])
            labels = video_data.get('labels', [])
            if partners or labels:
                with ui.row().classes('gap-1 flex-wrap'):
                    for partner in partners:
                        ui.chip(f"@{partner}", icon='person', color='secondary')
                    for label in labels:
                        ui.chip(f"#{label}", icon='label', color='primary')
    
    def _handle_video_click(self, video_id, event):
        """Handle video click"""
        if self.on_video_select:
            self.on_video_select(video_id, event)
        else:
            navigate_to_film(video_id, event)
    
    def get_same_day_videos_count(self):
        """Get count of videos from the same day"""
        video = self.video_state.get_video()
        if not video:
            return 0
        
        current_video_date = video.get('date', '').split('T')[0]
        if not current_video_date:
            return 0
        
        all_videos = load_videos()
        same_day_videos = [
            v for v in all_videos 
            if v['video_id'] != self.video_state.video_id 
            and v.get('date', '').split('T')[0] == current_video_date
        ]
        
        return len(same_day_videos)
    
    def get_current_video_date(self):
        """Get the current video date"""
        video = self.video_state.get_video()
        if not video:
            return ""
        
        return video.get('date', '').split('T')[0] 
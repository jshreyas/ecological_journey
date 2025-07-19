"""
ClipboardTab - Component for displaying and managing clips
Handles the clipboard functionality for viewing and managing clips
"""
from nicegui import ui
from .video_state import VideoState
from typing import Callable, Optional


class ClipboardTab:
    """Component for displaying and managing clips"""
    
    def __init__(self, video_state: VideoState, on_edit_clip: Callable = None, on_play_clip: Callable = None, on_share_clip: Callable = None):
        self.video_state = video_state
        self.on_edit_clip = on_edit_clip
        self.on_play_clip = on_play_clip
        self.on_share_clip = on_share_clip
        self.container = None
        
        # Register for video state refresh notifications
        self.video_state.add_refresh_callback(self.refresh)
    
    def create_tab(self, container, clip_id=None):
        """Create the clipboard tab UI"""
        self.container = container
        self.refresh(clip_id)
    
    def refresh(self, clip_id=None):
        """Refresh the clipboard tab with current video data"""
        if not self.container:
            return
            
        self.container.clear()
        with self.container:
            self._create_clipboard_ui(clip_id)
    
    def _create_clipboard_ui(self, clip_id=None):
        """Create the clipboard UI"""
        video = self.video_state.get_video()
        if not video:
            ui.label("No video data available")
            return
        
        clips = video.get("clips", [])
        if not clips:
            ui.label("No clips available").classes('text-gray-500 text-center p-4')
            return
        
        # Display clips in a grid
        for clip in clips:
            self._add_clip_card(clip, highlight=(clip.get('clip_id') == clip_id))
    
    def _add_clip_card(self, clip, highlight=False):
        """Add a clip card to the clipboard"""
        card_classes = 'w-full p-4 mb-2 cursor-pointer'
        if highlight:
            card_classes += ' bg-blue-50 border-2 border-blue-300'
        
        with ui.card().classes(card_classes):
            # Header with title and actions
            with ui.row().classes('justify-between items-center'):
                ui.label(clip.get('title', 'Untitled')).classes('font-semibold text-lg')
                with ui.row().classes('gap-1'):
                    if self.on_edit_clip:
                        ui.button(icon='edit', on_click=lambda e, c=clip: self._handle_edit_clip(c)).props('round dense')
                    if self.on_play_clip:
                        ui.button(icon='play', on_click=lambda e, c=clip: self._handle_play_clip(c)).props('round dense')
                    if self.on_share_clip:
                        ui.button(icon='share', on_click=lambda e, c=clip: self._handle_share_clip(c)).props('round dense')
            
            # Clip details
            start_time = clip.get('start', 0)
            end_time = clip.get('end', 0)
            duration = end_time - start_time
            
            with ui.row().classes('text-sm text-gray-600 mb-2'):
                ui.label(f"⏱️ {self._format_time(start_time)} - {self._format_time(end_time)}")
                ui.label(f"({self._format_time(duration)})")
                ui.label(f"🎬 {clip.get('speed', 1.0)}x")
            
            # Description
            description = clip.get('description', '')
            if description:
                ui.label(description).classes('text-sm text-gray-700 mb-2')
            
            # Partners and labels
            partners = clip.get('partners', [])
            labels = clip.get('labels', [])
            if partners or labels:
                with ui.row().classes('gap-1 flex-wrap'):
                    for partner in partners:
                        ui.chip(f"@{partner}", icon='person', color='secondary', )
                    for label in labels:
                        ui.chip(f"#{label}", icon='label', color='primary', )
    
    def _handle_edit_clip(self, clip):
        """Handle edit clip action"""
        if self.on_edit_clip:
            self.on_edit_clip(clip)
    
    def _handle_play_clip(self, clip):
        """Handle play clip action"""
        if self.on_play_clip:
            self.on_play_clip(clip)
    
    def _handle_share_clip(self, clip):
        """Handle share clip action"""
        if self.on_share_clip:
            self.on_share_clip(clip)
    
    def _format_time(self, seconds):
        """Format time in seconds to HH:MM:SS"""
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02}:{m:02}:{s:02}" if h else f"{m:02}:{s:02}"
    
    def get_video_data(self):
        """Get the current video data"""
        return self.video_state.get_video()
    
    def get_clips(self):
        """Get clips from the current video"""
        video = self.video_state.get_video()
        return video.get("clips", []) if video else [] 
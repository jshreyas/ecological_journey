"""
ShareDialogTab - Component for clip sharing functionality
Handles the clip sharing dialog and URL generation
"""
from nicegui import ui
from .video_state import VideoState
from typing import Callable, Optional
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL_SHARE = os.getenv("BASE_URL_SHARE")


class ShareDialogTab:
    """Component for clip sharing functionality"""
    
    def __init__(self, video_state: VideoState, on_share: Callable = None):
        self.video_state = video_state
        self.on_share = on_share
        self.container = None
        
        # Register for video state refresh notifications
        self.video_state.add_refresh_callback(self.refresh)
    
    def create_tab(self, container):
        """Create the share dialog tab UI"""
        self.container = container
        self.refresh()
    
    def refresh(self):
        """Refresh the share dialog tab"""
        if not self.container:
            return
        # Share dialog doesn't need refresh logic as it's created on demand
    
    def share_clip(self, clip):
        """Generate and show shareable link for a clip"""
        if self.on_share:
            self.on_share(clip)
        else:
            self._show_share_dialog(clip)
    
    def _show_share_dialog(self, clip):
        """Show the share dialog for a clip"""
        # Generate shareable link
        video_id = clip.get('video_id') or self.video_state.video_id
        clip_id = clip.get('clip_id')
        share_url = f"{BASE_URL_SHARE}/film/{video_id}?clip={clip_id}"

        with ui.dialog() as dialog, ui.card():
            ui.label('Share this clip').classes('font-bold mb-2')
            ui.input(value=share_url).props('readonly').classes('w-full').style('font-size:0.9em')
            ui.label('Copy the link above and share it with others.').classes('mt-2 text-xs text-gray-600')
            with ui.row().classes('w-full justify-between mt-4'):
                ui.button(
                    'Open Link',
                    on_click=lambda: ui.run_javascript(f'window.open("{share_url}", "_blank")')
                ).classes('mt-2')
                ui.button('Close', on_click=dialog.close).props('flat').classes('mt-1')
        dialog.open()
    
    def generate_share_url(self, clip) -> str:
        """Generate a shareable URL for a clip"""
        video_id = clip.get('video_id') or self.video_state.video_id
        clip_id = clip.get('clip_id')
        return f"{BASE_URL_SHARE}/film/{video_id}?clip={clip_id}"
    
    def get_base_share_url(self) -> str:
        """Get the base share URL"""
        return BASE_URL_SHARE or "" 
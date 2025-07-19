"""
ClipperTab - Component for creating and editing clips
Handles the clip creation and editing functionality
"""
from nicegui import ui
from utils.utils_api import add_clip_to_video, update_clip_in_video, get_playlist_id_for_video
from .video_state import VideoState
from typing import Callable, Optional


class ClipperTab:
    """Component for creating and editing clips"""
    
    def __init__(self, video_state: VideoState):
        self.video_state = video_state
        self.container = None
        self.on_edit_clip = None  # Will be set by external component
        
        # Register for video state refresh notifications
        self.video_state.add_refresh_callback(self.refresh)
    
    def create_tab(self, container):
        """Create the clipper tab UI"""
        self.container = container
        self.refresh()
    
    def refresh(self):
        """Refresh the clipper tab with current video data"""
        if not self.container:
            return
            
        self.container.clear()
        with self.container:
            self._create_clipper_ui()
    
    def _create_clipper_ui(self):
        """Create the clipper editing UI"""
        video = self.video_state.get_video()
        if not video:
            ui.label("No video data available")
            return
        
        # Display existing clips
        clips = video.get("clips", [])
        if clips:
            ui.label(f"Existing clips ({len(clips)}):").classes('text-lg font-semibold')
            for clip in clips:
                self._add_clip_card(clip)
        else:
            ui.label("No clips yet. Create your first clip below.").classes('text-gray-500')
        
        ui.separator()
        
        # Create new clip form
        ui.label("Create new clip:").classes('text-lg font-semibold')
        self._create_clip_form()
    
    def _add_clip_card(self, clip):
        """Add a clip card to the UI"""
        with ui.card().classes('w-full p-4 mb-2'):
            with ui.row().classes('justify-between items-center'):
                ui.label(clip.get('title', 'Untitled')).classes('font-semibold')
                with ui.row().classes('gap-2'):
                    if self.on_edit_clip:
                        ui.button(icon='edit', on_click=lambda e, c=clip: self.on_edit_clip(c)).props('round dense')
                    ui.button(icon='play', on_click=lambda e, c=clip: self._play_clip(c)).props('round dense')
            
            # Clip details
            start_time = clip.get('start', 0)
            end_time = clip.get('end', 0)
            duration = end_time - start_time
            
            with ui.row().classes('text-sm text-gray-600'):
                ui.label(f"Start: {self._format_time(start_time)}")
                ui.label(f"End: {self._format_time(end_time)}")
                ui.label(f"Duration: {self._format_time(duration)}")
                ui.label(f"Speed: {clip.get('speed', 1.0)}x")
            
            # Partners and labels
            partners = clip.get('partners', [])
            labels = clip.get('labels', [])
            if partners or labels:
                with ui.row().classes('gap-1 flex-wrap'):
                    for partner in partners:
                        ui.chip(f"@{partner}", icon='person', color='secondary')
                    for label in labels:
                        ui.chip(f"#{label}", icon='label', color='primary')
    
    def _create_clip_form(self):
        """Create the new clip form"""
        video = self.video_state.get_video()
        duration = video.get('duration_seconds', 0)
        
        with ui.card().classes('w-full p-4'):
            # Title input
            title_input = ui.input('Clip Title', placeholder='Enter clip title').classes('w-full')
            
            # Time range inputs
            with ui.row().classes('gap-4'):
                start_input = ui.number('Start Time (seconds)', min=0, max=duration, value=0).classes('w-1/2')
                end_input = ui.number('End Time (seconds)', min=0, max=duration, value=min(60, duration)).classes('w-1/2')
            
            # Speed input
            speed_input = ui.number('Speed', min=0.25, max=2.0, step=0.25, value=1.0).classes('w-full')
            
            # Description
            description_input = ui.textarea('Description', placeholder='Optional description').props('rows=3').classes('w-full')
            
            # Partners and labels
            chips_input_ref, chips_list, chips_error, chips_container = self._create_chips_input()
            
            # Save button
            with ui.row().classes('justify-end gap-2 mt-4'):
                ui.button(icon='save', on_click=lambda: self._save_clip(
                    title_input, start_input, end_input, speed_input, 
                    description_input, chips_list
                )).props('color=primary')
    
    def _create_chips_input(self, initial=None):
        """Create chips input for partners and labels"""
        initial = initial or []
        chips_list = initial.copy()
        container = ui.row().classes('gap-2')
        input_ref = ui.input('Add @partner or #label').classes('w-full').props('dense')
        error_label = ui.label().classes('text-red-500 text-xs')

        def add_chip():
            val = input_ref.value.strip()
            if not val:
                return
            if not (val.startswith('@') or val.startswith('#')):
                error_label.text = "Start with @ for partners or # for labels"
                return
            if val in chips_list:
                error_label.text = "Already added"
                return
            error_label.text = ""
            chips_list.append(val)
            with container:
                ui.chip(val, icon='person' if val.startswith('@') else 'label', color='secondary' if val.startswith('@') else 'primary', removable=True).on('remove', lambda e, v=val: chips_list.remove(v))
            input_ref.value = ''

        input_ref.on('keydown.enter', add_chip)
        with input_ref.add_slot('append'):
            ui.button(icon='add', on_click=add_chip).props('round dense flat')
        # Render initial chips
        with container:
            for val in chips_list:
                ui.chip(val, icon='person' if val.startswith('@') else 'label', color='secondary' if val.startswith('@') else 'primary', removable=True).on('remove', lambda e, v=val: chips_list.remove(v))
        return input_ref, chips_list, error_label, container
    
    def _save_clip(self, title_input, start_input, end_input, speed_input, description_input, chips_list):
        """Save the new clip"""
        import uuid
        from dialog_puns import caught_john_doe
        from nicegui import app
        
        # Extract data
        title = title_input.value.strip()
        if not title:
            ui.notify("❌ Clip title is required", type="negative")
            return
        
        start_time = start_input.value
        end_time = end_input.value
        if start_time >= end_time:
            ui.notify("❌ End time must be after start time", type="negative")
            return
        
        speed = speed_input.value
        description = description_input.value.strip()
        
        partners_list = [c[1:] for c in chips_list if c.startswith('@')]
        labels_list = [c[1:] for c in chips_list if c.startswith('#')]
        
        # Create clip data
        clip_data = {
            'clip_id': str(uuid.uuid4()),
            'title': title,
            'start': start_time,
            'end': end_time,
            'speed': speed,
            'description': description,
            'labels': labels_list,
            'partners': partners_list,
        }
        
        # Save to API
        token = app.storage.user.get("token")
        if not token:
            caught_john_doe()
            return
        
        try:
            video = self.video_state.get_video()
            playlist_name = get_playlist_id_for_video(video['video_id'])
            add_clip_to_video(playlist_name, video['video_id'], clip_data, token)
            
            ui.notify("✅ Clip created successfully", type="positive")
            self.video_state.refresh()
            
            # Clear form
            title_input.value = ""
            start_input.value = 0
            end_input.value = min(60, video.get('duration_seconds', 60))
            speed_input.value = 1.0
            description_input.value = ""
            chips_list.clear()
            
        except Exception as e:
            ui.notify(f"❌ Failed to create clip: {e}", type="negative")
    
    def _play_clip(self, clip):
        """Play a clip (placeholder for now)"""
        ui.notify(f"▶️ Playing: {clip['title']}", type="info")
    
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
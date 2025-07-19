"""
ClipperTab - Component for creating and editing clips
Handles the clip creation and editing functionality
"""
from nicegui import ui
from utils.utils_api import add_clip_to_video, update_clip_in_video, get_playlist_id_for_video
from .video_state import VideoState
from typing import Callable, Optional
from dialog_puns import generate_funny_title


class ClipperTab:
    """Component for creating and editing clips"""
    
    def __init__(self, video_state: VideoState):
        self.video_state = video_state
        self.container = None
        self.on_edit_clip = None  # Will be set by external component
        self.mode = 'add'
        self.current_edit_clip = None
        self.video_state.add_refresh_callback(self.refresh)
    
    def create_tab(self, container):
        self.container = container
        self.refresh()
    
    def refresh(self):
        if not self.container:
            return
        self.container.clear()
        with self.container:
            self._show_clip_form(self.current_edit_clip, is_new=(self.mode == 'add'))

    def force_refresh(self):
        # Public method to force a UI refresh (if needed externally)
        self.refresh()

    def _on_edit(self, clip):
        self.mode = 'edit'
        self.current_edit_clip = clip
        self.refresh()
    
    def _show_clip_form(self, clip=None, is_new=True):
        import uuid
        from dialog_puns import caught_john_doe
        from nicegui import app
        video = self.video_state.get_video()
        duration = video.get('duration_seconds', 0)
        if is_new or not clip:
            clip_id = str(uuid.uuid4())
            funny_title = generate_funny_title()
            clip = {
                'clip_id': clip_id,
                'title': funny_title,
                'start': 0,
                'end': min(10, duration),
                'speed': 1.0,
                'description': '',
                'labels': [],
                'partners': [],
            }
        start_val = int(clip.get('start', 0))
        end_val = int(clip.get('end', min(10, duration)))
        with ui.card().classes('w-full p-4 mt-2'):
            with ui.splitter(horizontal=False, value=70).classes('w-full') as splitter:
                with splitter.before:
                    title = ui.input('Title', value=clip.get('title', '')).classes('w-full')
                with splitter.after:
                    with ui.column().classes('w-full h-full justify-center items-center'):
                        speed_knob = ui.knob(
                            min=0.25, max=2.0, step=0.25, value=clip.get('speed', 1.0),
                            track_color='grey-2', show_value=True
                        ).props('size=60')
                        ui.label('Speed').classes('text-center text-xs w-full')
            # Double-ended range slider
            range_slider = ui.range(
                min=0,
                max=duration,
                value={'min': start_val, 'max': end_val},
            ).classes('w-full')
            # Editable timestamp fields under the slider
            def seconds_to_hms(seconds):
                seconds = int(seconds)
                h = seconds // 3600
                m = (seconds % 3600) // 60
                s = seconds % 60
                return f"{h:02}:{m:02}:{s:02}" if h else f"{m:02}:{s:02}"
            def hms_to_seconds(hms):
                parts = [int(p) for p in hms.split(':')]
                if len(parts) == 3:
                    return parts[0]*3600 + parts[1]*60 + parts[2]
                elif len(parts) == 2:
                    return parts[0]*60 + parts[1]
                else:
                    return 0
            with ui.row().classes('w-full justify-between items-center'):
                start_input = ui.input(
                    value=seconds_to_hms(start_val)
                ).props('type=text').props('dense').classes('w-12 text-xs')
                end_input = ui.input(
                    value=seconds_to_hms(end_val)
                ).props('type=text').props('dense').classes('w-12 text-xs text-right')
            # Two-way binding logic
            def update_inputs_from_slider():
                v = range_slider.value
                start_input.value = seconds_to_hms(int(v['min']))
                end_input.value = seconds_to_hms(int(v['max']))
            def update_slider_from_inputs():
                try:
                    s = max(0, min(duration, hms_to_seconds(start_input.value)))
                    e = max(0, min(duration, hms_to_seconds(end_input.value)))
                    if s > e:
                        s, e = e, s
                    range_slider.value = {'min': s, 'max': e}
                except Exception:
                    pass
            range_slider.on('update:model-value', lambda e: update_inputs_from_slider())
            start_input.on('blur', lambda e: update_slider_from_inputs())
            end_input.on('blur', lambda e: update_slider_from_inputs())
            start_input.on('keydown.enter', lambda e: update_slider_from_inputs())
            end_input.on('keydown.enter', lambda e: update_slider_from_inputs())
            update_inputs_from_slider()
            # Chips input for @partners and #labels
            chips_input_ref, chips_list, chips_error, chips_container = self._create_chips_input(
                [f'@{p}' for p in clip.get('partners', [])] + [f'#{l}' for l in clip.get('labels', [])]
            )
            # Notes textarea
            notes_input = ui.textarea(
                'Notes',
                value=clip.get('description', '')
            ).props('rows=4').classes('w-full')
            with ui.row().classes('justify-end gap-2 mt-4'):
                def save_clip():
                    partners_list = [c[1:] for c in chips_list if c.startswith('@')]
                    labels_list = [c[1:] for c in chips_list if c.startswith('#')]
                    updated_clip = {
                        'clip_id': clip.get('clip_id'),
                        'title': title.value,
                        'start': hms_to_seconds(start_input.value),
                        'end': hms_to_seconds(end_input.value),
                        'description': notes_input.value,
                        'labels': labels_list,
                        'partners': partners_list,
                        'speed': speed_knob.value,
                    }
                    token = app.storage.user.get("token")
                    if not token:
                        caught_john_doe()
                        return
                    try:
                        video = self.video_state.get_video()
                        playlist_name = get_playlist_id_for_video(video['video_id'])
                        if is_new:
                            add_clip_to_video(playlist_name, video['video_id'], updated_clip, token)
                            ui.notify("✅ Clip created successfully", type="positive")
                        else:
                            update_clip_in_video(playlist_name, video['video_id'], updated_clip, token)
                            ui.notify("✅ Clip updated successfully", type="positive")
                        self.mode = 'add'
                        self.current_edit_clip = None
                        self.video_state.refresh()
                    except Exception as e:
                        ui.notify(f"❌ Failed to save clip: {e}", type="negative")
                def reset_to_add_mode():
                    self.mode = 'add'
                    self.current_edit_clip = None
                    self.refresh()
                ui.button(icon='save', on_click=save_clip).props('color=primary')
                ui.button(icon='close', on_click=reset_to_add_mode).props('color=secondary')
    
    def _on_cancel(self):
        self.mode = 'add'
        self.current_edit_clip = None
        self.refresh()
    
    def _add_clip_card(self, clip):
        with ui.card().classes('w-full p-4 mb-2'):
            with ui.row().classes('justify-between items-center'):
                ui.label(clip.get('title', 'Untitled')).classes('font-semibold')
                with ui.row().classes('gap-2'):
                    ui.button(icon='edit', on_click=lambda e, c=clip: self._on_edit(c)).props('round dense')
                    ui.button(icon='play', on_click=lambda e, c=clip: self._play_clip(c)).props('round dense')
            start_time = clip.get('start', 0)
            end_time = clip.get('end', 0)
            duration = end_time - start_time
            with ui.row().classes('text-sm text-gray-600'):
                ui.label(f"Start: {self._format_time(start_time)}")
                ui.label(f"End: {self._format_time(end_time)}")
                ui.label(f"Duration: {self._format_time(duration)}")
                ui.label(f"Speed: {clip.get('speed', 1.0)}x")
            partners = clip.get('partners', [])
            labels = clip.get('labels', [])
            if partners or labels:
                with ui.row().classes('gap-1 flex-wrap'):
                    for partner in partners:
                        ui.chip(f"@{partner}", icon='person', color='secondary')
                    for label in labels:
                        ui.chip(f"#{label}", icon='label', color='primary')
    
    def _create_chips_input(self, initial=None):
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
        with container:
            for val in chips_list:
                ui.chip(val, icon='person' if val.startswith('@') else 'label', color='secondary' if val.startswith('@') else 'primary', removable=True).on('remove', lambda e, v=val: chips_list.remove(v))
        return input_ref, chips_list, error_label, container
    
    def _play_clip(self, clip):
        ui.notify(f"▶️ Playing: {clip['title']}", type="info")
    
    def _format_time(self, seconds):
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02}:{m:02}:{s:02}" if h else f"{m:02}:{s:02}"
    
    def get_video_data(self):
        return self.video_state.get_video()
    
    def get_clips(self):
        video = self.video_state.get_video()
        return video.get("clips", []) if video else []

    def edit_clip(self, clip):
        self.mode = 'edit'
        self.current_edit_clip = clip
        self.refresh() 
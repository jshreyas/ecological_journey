# film.py
from nicegui import ui, app
from utils.dialog_puns import caught_john_doe, generate_funny_title
from utils.video_player import VideoPlayer
from utils.utils_api import add_clip_to_video, update_clip_in_video, get_playlist_id_for_video, load_video, load_videos, save_video_metadata
from utils.utils import format_time
from films import navigate_to_film
from datetime import datetime
from film_components import (
    VideoState, FilmdataTab, ClipperTab, ClipboardTab, MetaforgeTab,
    FilmboardTab, NavigationTab, PlayerControlsTab, ShareDialogTab
)
import os
import json
import uuid
from dotenv import load_dotenv
load_dotenv()


BASE_URL_SHARE = os.getenv("BASE_URL_SHARE")

#TODO: Make this page mobile friendly for logged in user for write access
def film_page(video_id: str):
    # Initialize VideoState for centralized state management
    video_state = VideoState(video_id)

    state = {'latest_cleaned': None}  # Will store cleaned copy for confirm step
    diff_area = None       # Will be bound to markdown component
    confirm_dialog = None  # Will be bound to dialog

    query_params = ui.context.client.request.query_params
    clip_id = query_params.get("clip")
    play_clips_playlist = query_params.get("clips", "false").lower() == "true"
    autoplay_clip = None
    if clip_id:
        video = video_state.get_video()
        if not video:
            ui.label(f"⚠️ Video: {video_id} not found!")
            return
        clips = video.get("clips", [])
        autoplay_clip = next((c for c in clips if c['clip_id'] == clip_id), None)
        if not autoplay_clip:
            ui.label(f"⚠️ Clip: {clip_id} not found in video {video_id}!")
            return
        video_id = autoplay_clip.get('video_id', video_id)
        # Reinitialize video_state if video_id changed
        if video_id != video_state.video_id:
            video_state = VideoState(video_id)

    # State to track which clip is being edited (or None for new)
    clip_form_state = {'clip': None, 'is_new': True}
    clip_form_container = {}

    def finalize_save():
        confirm_dialog.close()
        print(f"Finalizing save...: {state['latest_cleaned']}")
        success = save_video_metadata(state['latest_cleaned'], app.storage.user.get("token"))
        if success:
            ui.notify("✅ Filmdata published", type="positive")
            # Clear the state to prevent cumulative delta tracking
            state['latest_cleaned'] = None
            # Refresh video state and notify all components
            video_state.refresh()
        else:
            ui.notify("❌ Failed to publish filmdata", type="negative")

    confirm_dialog = ui.dialog()
    with confirm_dialog:
        with ui.card().classes('max-w-xl'):
            ui.label('📝 Review Changes').classes('text-lg font-bold')
            diff_area = ui.markdown('').classes('text-sm text-left whitespace-pre-wrap max-h-80 overflow-auto')
            with ui.row().classes('justify-end w-full'):
                ui.button(icon='close', on_click=confirm_dialog.close)
                ui.button(icon='save', color='primary', on_click=lambda: finalize_save())

    def show_clip_form(clip, is_new=False):
        clip_form_container['container'].clear()
        with clip_form_container['container']:
            video = video_state.get_video()
            duration = video.get('duration_seconds', 0)
            start_val = int(clip.get('start', 0))
            end_val = clip.get('end')
            if not end_val:
                end_val = duration if duration > 0 else start_val + 10
            end_val = int(min(end_val, duration))

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

            with ui.card().classes('w-full p-4 mt-2'):
                with ui.splitter(horizontal=False, value=70).classes('w-full') as splitter:
                    with splitter.before:
                        title = ui.input('Title', value=clip.get('title', '')).classes('w-full')
                    with splitter.after:
                        # --- Speed input ---
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
                with ui.row().classes('w-full justify-between items-center'):
                    start_input = ui.input(
                        value=seconds_to_hms(start_val)
                    ).props('type=text').props('dense').classes('w-12 text-xs')
                    end_input = ui.input(
                        value=seconds_to_hms(end_val)
                    ).props('type=text').props('dense').classes('w-12 text-xs text-right')

                # --- Two-way binding logic ---
                def update_inputs_from_slider():
                    v = range_slider.value
                    start_input.value = seconds_to_hms(int(v['min']))
                    end_input.value = seconds_to_hms(int(v['max']))

                def update_slider_from_inputs():
                    try:
                        s = max(0, min(duration, hms_to_seconds(start_input.value)))
                        e = max(0, min(duration, hms_to_seconds(end_input.value)))
                        # Ensure start <= end
                        if s > e:
                            s, e = e, s
                        range_slider.value = {'min': s, 'max': e}
                    except Exception:
                        pass  # Ignore invalid input

                range_slider.on('update:model-value', lambda e: update_inputs_from_slider())
                start_input.on('blur', lambda e: update_slider_from_inputs())
                end_input.on('blur', lambda e: update_slider_from_inputs())
                start_input.on('keydown.enter', lambda e: update_slider_from_inputs())
                end_input.on('keydown.enter', lambda e: update_slider_from_inputs())
                update_inputs_from_slider()

                # --- Chips input for @partners and #labels ---
                chips_input_ref, chips_list, chips_error, chips_container = chips_input_combined(
                    [f'@{p}' for p in clip.get('partners', [])] + [f'#{l}' for l in clip.get('labels', [])]
                )

                # --- Notes textarea ---
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
                            'speed': speed_knob.value,  # <-- This now reads the current value
                        }
                        playlist_name = get_playlist_id_for_video(video_id)
                        token = app.storage.user.get("token")
                        if not token:
                            caught_john_doe()
                            return
                        try:
                            if is_new:
                                add_clip_to_video(playlist_name, video_id, updated_clip, token)
                                ui.notify("✅ Clip created successfully", type="positive")
                            else:
                                update_clip_in_video(playlist_name, video_id, updated_clip, token)
                                ui.notify("✅ Clip updated successfully", type="positive")
                            video_state.refresh()
                            reset_to_add_mode()
                        except Exception as e:
                            ui.notify(f"❌ Failed to save clip: {e}", type="negative")

                    def reset_to_add_mode():
                        # Reset to add mode after save/cancel
                        clip_id = str(uuid.uuid4())
                        funny_title = generate_funny_title()
                        clip_form_state['clip'] = {
                            'clip_id': clip_id,
                            'title': funny_title,
                            'start': 0,
                            'end': 0,
                            'description': '',
                            'labels': [],
                            'partners': [],
                        }
                        clip_form_state['is_new'] = True
                        show_clip_form(clip_form_state['clip'], is_new=True)

                    ui.button(icon='save', on_click=save_clip).props('color=primary')
                    ui.button(icon='close', on_click=reset_to_add_mode).props('color=secondary')

    # Initialize components
    navigation_tab = NavigationTab(video_state)
    player_controls_tab = PlayerControlsTab(video_state)
    share_dialog_tab = ShareDialogTab(video_state)
    filmdata_tab = FilmdataTab(video_state)
    clipper_tab = ClipperTab(video_state)
    metaforge_tab = MetaforgeTab(video_state)
    filmboard_tab = FilmboardTab(video_state)

    def on_edit_clip(clip):
        tabs.value = tab_clipmaker  # Switch to Clip Maker tab
        # Use a short timer to ensure the tab is visible before loading the clip
        ui.timer(0.05, lambda: clipper_tab.edit_clip(clip), once=True)

    clipboard_tab = ClipboardTab(
        video_state,
        on_edit_clip=on_edit_clip,
        on_play_clip=player_controls_tab.play_clip,
        on_share_clip=share_dialog_tab.share_clip
    )

    # Inline render_film_editor functionality
    with ui.column().classes('w-full'):
        # Navigation
        with ui.row().classes('w-full justify-between items-center') as navigation_container:
            navigation_tab.create_tab(navigation_container)

        with ui.splitter(horizontal=False, value=70).classes('w-full h-[70vh] rounded shadow') as splitter:
            with splitter.before:
                with ui.column().classes('w-full h-full p-4 gap-4') as player_container_ref:
                    player_controls_tab.create_tab(player_container_ref, play_clips_playlist, autoplay_clip)

            with splitter.after:
                video = load_video(video_id)
                with ui.tabs().classes('w-full') as tabs:
                    tab_videom = ui.tab('Filmdata').tooltip('Edit film metadata like title, date, partners, labels')
                    tab_clipmaker = ui.tab('Clipper').tooltip('Create and edit clips from the film')
                    tab_bulk = ui.tab('metaforge').tooltip('Bulk edit film and clip metadata in JSON format')
                with ui.tab_panels(tabs, value=tab_bulk).classes('w-full h-full'):

                    # Create tab panels using components
                    with ui.tab_panel(tab_videom) as filmdata_container:
                        filmdata_tab.create_tab(filmdata_container)
                    
                    with ui.tab_panel(tab_clipmaker) as clipper_container:
                        clipper_tab.create_tab(clipper_container)
                    
                    with ui.tab_panel(tab_bulk).classes('w-full h-full mt-0') as metaforge_container:
                        metaforge_tab.create_tab(metaforge_container)

            with splitter.separator:
                ui.icon('drag_indicator').classes('text-gray-400')

        ui.separator().classes('w-full mt-2')
        with ui.splitter(value=50).classes('w-full h-[600px]') as splitter:
            with splitter.before:
                # Filmboard heading with count
                current_video_date = filmboard_tab.get_current_video_date()
                same_day_count = filmboard_tab.get_same_day_videos_count()
                with ui.column().classes('w-full h-full rounded-lg'):
                    if current_video_date:
                        ui.label(f'🎥 More films from 🗓️ {datetime.strptime(current_video_date, "%Y-%m-%d").strftime("%B %d, %Y")} ({same_day_count + 1})').classes('text-xl ml-2 font-semibold')
                    else:
                        ui.label('🎥 More films from the same day').classes('text-xl ml-2 font-semibold')
                    with ui.grid().classes('grid auto-rows-max grid-cols-[repeat(auto-fit,minmax(250px,1fr))] w-full p-2 bg-white rounded-lg shadow-lg') as filmboard_container:
                        filmboard_tab.create_tab(filmboard_container)
            with splitter.after:
                # Clipboard heading with count
                video = load_video(video_id)
                clips = video.get("clips", [])
                with ui.column().classes('w-full h-full rounded-lg'):
                    ui.label(f'📋 Clipboard ({len(clips)})').classes('text-xl font-semibold ml-2')
                    with ui.grid().classes('grid auto-rows-max grid-cols-[repeat(auto-fit,minmax(250px,1fr))] w-full p-2 bg-white rounded-lg shadow-lg') as clipboard_container:
                        clipboard_tab.create_tab(clipboard_container, clip_id)

def chips_input_combined(initial=None):
    """Single chips input for both partners (@) and labels (#)."""
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

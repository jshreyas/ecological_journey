# film.py
from nicegui import ui, app
from dialog_puns import caught_john_doe, generate_funny_title
from video_player import VideoPlayer
from utils_api import load_video, load_videos, save_video_metadata
from utils_api import add_clip_to_video, update_clip_in_video, get_playlist_id_for_video
from utils import format_time
from films import navigate_to_film
import random
import os
import uuid
from dotenv import load_dotenv
load_dotenv()


BASE_URL_SHARE = os.getenv("BASE_URL_SHARE")


def film_page(video_id: str):
    query_params = ui.context.client.request.query_params
    clip_id = query_params.get("clip")
    play_clips_playlist = query_params.get("clips", "false").lower() == "true"
    autoplay_clip = None
    if clip_id:
        video = load_video(video_id)
        if not video:
            ui.label(f"⚠️ Video: {video_id} not found!")
            return
        clips = video.get("clips", [])
        autoplay_clip = next((c for c in clips if c['clip_id'] == clip_id), None)
        if not autoplay_clip:
            ui.label(f"⚠️ Clip: {clip_id} not found in video {video_id}!")
            return
        video_id = autoplay_clip.get('video_id', video_id)
    player_container = {'ref': None}
    player_speed = {'value': 1.0}

    video = load_video(video_id)
    if not video:
        ui.label(f"⚠️ Video: {video_id} not found!")
        return

    # State to track which clip is being edited (or None for new)
    clip_form_state = {'clip': None, 'is_new': True}
    clip_form_container = {}

    def show_clip_form(clip, is_new=False):
        clip_form_container['container'].clear()
        with clip_form_container['container']:
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
                            refresh_clipboard()
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

                    ui.button('Save', on_click=save_clip).props('color=primary')
                    ui.button('Cancel', on_click=reset_to_add_mode).props('color=secondary')

    def on_edit_clip(clip):
        clip_form_state['clip'] = clip
        clip_form_state['is_new'] = False
        tabs.value = tab_clipmaker  # Switch to Clip Maker tab
        show_clip_form(clip, is_new=False)

    def play_clip(clip):
        ui.notify(
            f"▶️ Playing: {clip['title']} at {clip.get('speed', 1.0)}x",
            type="info",
            position="bottom",
            timeout=3000
        )
        start_time = clip.get("start", 0)
        speed = clip.get("speed", 1.0)
        ref = player_container['ref']
        if ref:
            ref.clear()
            with ref:
                VideoPlayer(video_id, start=start_time, end=clip.get("end"), speed=speed, parent=ref)

   # --- Playlist mode: play all clips in sequence ---
    clips_playlist_state = {'index': 0, 'clips': []}

    def play_clips_playlist_mode():
        video = load_video(video_id)
        clips = video.get("clips", [])
        if not clips:
            ui.notify("No clips to play.", type="warning")
            return
        clips_playlist_state['clips'] = clips
        clips_playlist_state['index'] = 0

        def play_next_clip():
            idx = clips_playlist_state['index']
            if idx >= len(clips):
                # ui.notify("✅ Finished all clips.", type="positive")
                return
            clip = clips[idx]
            start_time = clip.get("start", 0)
            end_time = clip.get("end")
            speed = clip.get("speed", 1.0)
            ref = player_container['ref']
            if ref:
                ref.clear()
                with ref:
                    VideoPlayer(
                        video_id,
                        start=start_time,
                        end=end_time,
                        speed=speed,
                        on_end=lambda: next_clip_callback(),
                        parent=ref
                    )
            # Notify after UI update to ensure it always shows
            # ui.timer(
            #     0,
            #     lambda: ui.notify(
            #         f"▶️ Playing clip {idx+1}/{len(clips)}: {clip['title']}",
            #         type="info",
            #         timeout=2000
            #     ),
            #     once=True
            # )

        def next_clip_callback():
            clips_playlist_state['index'] += 1
            play_next_clip()

        play_next_clip()

    def add_clip_card(clip, highlight=False, autoplay=False):
        with ui.card().classes(
            f"p-2 flex flex-col justify-between{' border-2 border-blue-500' if highlight else ''}"
        ):
            with ui.column().classes('w-full gap-2'):
                ui.label(clip["title"]).classes('font-medium text-sm truncate')
                with ui.row().classes('w-full gap-2 justify-between'):
                    start_time = format_time(clip.get('start', 0))
                    end_time = format_time(clip.get('end', 0))
                    ui.label(f"⏱ {start_time} - {end_time}").classes('text-xs')
                    ui.label(f"{format_time(clip.get('end', 0) - clip.get('start', 0))}").classes('text-xs')
            # --- Partners (clip in black, video in primary blue) ---
            partners = clip.get('partners', [])
            video_partners = video.get('partners', [])
            partners_html = ""
            #TODO: bug: when no partners in clip but in video metadata, then "No partners" is also shown along with video partners
            if partners:
                partners_html = ", ".join(f"<span style='color:black'>{p}</span>" for p in partners)
            if video_partners:
                if partners_html:
                    partners_html += ", "
                partners_html += ", ".join(f"<span style='color:var(--q-primary)'>{p}</span>" for p in video_partners)
            if not partners_html:
                partners_html = "No partners"
            ui.html(f"🎭 {partners_html}").classes('text-xs')

            # --- Labels (clip in black, video in primary blue) ---
            labels = clip.get('labels', [])
            video_labels = video.get('labels', [])
            labels_html = ""
            if labels:
                labels_html = ", ".join(f"<span style='color:black'>{l}</span>" for l in labels)
            if video_labels:
                if labels_html:
                    labels_html += ", "
                labels_html += ", ".join(f"<span style='color:var(--q-primary)'>{l}</span>" for l in video_labels)
            if not labels_html:
                labels_html = "No labels"
            ui.html(f"🏷️ {labels_html}").classes('text-xs')

            with ui.row().classes('justify-end gap-2 mt-2'):
                ui.button(icon='play_arrow', on_click=lambda: play_clip(clip)).props('flat color=primary').tooltip('Play')
                ui.button(icon='edit', on_click=lambda: on_edit_clip(clip)).props('flat color=secondary').tooltip('Edit')
                ui.button(icon='share', on_click=lambda: share_clip(clip)).props('flat color=accent').tooltip('Share')
            # Optionally, auto-play the clip if requested
            if autoplay:
                play_clip(clip)

    def share_clip(clip):
        # Generate shareable link
        video_id = clip.get('video_id') or 'unknown'
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

    def refresh_clipboard():
        clipboard_container.clear()
        with clipboard_container:
            video = load_video(video_id)
            clips = video.get("clips", [])
            if not clips:
                ui.label("📭 No clips for this film yet.").classes('text-sm text-gray-500')
                return
            for clip in clips:
                clip['video_id'] = video_id  # <-- Ensure video_id is present
                if clip_id and clip['clip_id'] == clip_id:
                    add_clip_card(clip, highlight=True, autoplay=True)
                else:
                    add_clip_card(clip)

    def handle_publish(video_metadata=None):
        token = app.storage.user.get("token")
        if not token:
            caught_john_doe()
            return
        try:
            # Merge with required fields from the loaded video
            for key in ["video_id", "youtube_url", "title", "date", "duration_seconds"]:
                video_metadata[key] = video.get(key)
            # 🛑 Preserve existing clips!
            video_metadata["clips"] = video.get("clips", [])
            success = save_video_metadata(video_metadata, token)
            if success:
                ui.notify("✅ Filmdata published", type="positive")
            else:
                ui.notify("❌ Failed to publish filmdata", type="negative")
        except Exception as e:
            ui.notify(f"❌ Error: {e}", type="negative")

    def refresh_filmboard():
        """Refresh the Filmboard section with videos from the same day."""
        filmboard_container.clear()
        with filmboard_container:
            # Get the date of the current video
            current_video_date = video.get('date', '').split('T')[0]
            if not current_video_date:
                ui.label("⚠️ No date available for the current video.").classes('text-sm text-gray-500')
                return

            # Load all videos and filter by the same date
            all_videos = load_videos()
            same_day_videos = [v for v in all_videos if v.get('date', '').startswith(current_video_date) and v['video_id'] != video_id]

            if not same_day_videos:
                ui.label("📭 No other films found from the same day.").classes('text-sm text-gray-500')
                return

            # Display thumbnails for videos from the same day
            for v in same_day_videos:
                partners = v.get("partners", [])
                labels = v.get("labels", [])
                partners_html = ", ".join(p for p in partners) if partners else "No partners"
                labels_html = ", ".join(l for l in labels) if labels else "No labels"
                with ui.card().classes(
                    'cursor-pointer flex flex-row flex-col p-2 hover:shadow-xl transition-shadow duration-200 border-gray-600'
                ).on('click', lambda e, vid=v['video_id']: navigate_to_film(vid, e)):
                    with ui.row().classes('w-full gap-2 justify-between'):
                        ui.label(v["title"]).tooltip(v["title"]).classes('truncate font-bold text-sm sm:text-base')
                        ui.label(f"⏱ {v['duration_human']}").classes('text-xs')
                    ui.label(f"🎭 {partners_html}").classes('text-xs')
                    ui.label(f"🏷️ {labels_html}").classes('text-xs')
                    with ui.row().classes('w-full gap-2 justify-between'):
                        ui.label(f"📂 {v['playlist_name']}").classes('text-xs text-blue-500')
                        ui.label(f"🎬 {len(v.get('clips', 0))}").classes('text-xs')

    def get_adjacent_videos():
        """Find the last video from the previous day and the first video from the next day."""
        all_videos = load_videos()
        current_video_date = video.get('date', '').split('T')[0]

        if not current_video_date:
            return None, None

        # Sort videos by date
        sorted_videos = sorted(all_videos, key=lambda v: v.get('date', ''))
        prev_video = None
        next_video = None

        for i, v in enumerate(sorted_videos):
            if v['video_id'] == video_id:
                # Find the last video from the previous day
                for j in range(i - 1, -1, -1):
                    if sorted_videos[j]['date'].split('T')[0] < current_video_date:
                        prev_video = sorted_videos[j]
                        break

                # Find the first video from the next day
                for j in range(i + 1, len(sorted_videos)):
                    if sorted_videos[j]['date'].split('T')[0] > current_video_date:
                        next_video = sorted_videos[j]
                        break
                break

        return prev_video, next_video

    prev_video, next_video = get_adjacent_videos()

    # Inline render_film_editor functionality
    with ui.column().classes('w-full p-4 gap-6'):

        # Navigation Arrows
        with ui.row().classes('w-full justify-between items-center mb-4'):
            # Use a 3-column grid for consistent centering
            with ui.grid(columns=3).classes('w-full items-center'):
                # Previous
                if prev_video:
                    with ui.row().classes('items-center cursor-pointer justify-start').on('click', lambda e: navigate_to_film(prev_video['video_id'], e)):
                        ui.icon('arrow_back').classes('text-blue-500')
                        ui.label(f"Previous: {prev_video['title']}").classes('text-sm text-blue-500 truncate')
                else:
                    ui.label().classes('')  # Empty cell

                # Center label
                with ui.row().classes('justify-center'):
                    ui.label(f'🎬 Studying: {video.get("title", "Untitled Video")}').classes('text-2xl font-bold')

                # Next
                if next_video:
                    with ui.row().classes('items-center cursor-pointer justify-end').on('click', lambda e: navigate_to_film(next_video['video_id'], e)):
                        ui.label(f"Next: {next_video['title']}").classes('text-sm text-blue-500 truncate')
                        ui.icon('arrow_forward').classes('text-blue-500')
                else:
                    ui.label().classes('')  # Empty cell

        player_container_ref = None

        with ui.splitter(horizontal=False, value=70).classes('w-full h-[70vh] rounded shadow') as splitter:
            with splitter.before:
                with ui.column().classes('w-full h-full p-4 gap-4') as player_container_ref:
                    player_container['ref'] = player_container_ref  # Set ref first!
                    if play_clips_playlist:
                        with player_container_ref:
                            play_clips_playlist_mode()
                            # ui.label("Loading playlist...").classes('text-center text-gray-400')
                    elif autoplay_clip:
                        play_clip(autoplay_clip)
                    else:
                        VideoPlayer(video_id, speed=player_speed['value'], parent=player_container_ref)
                player_container['ref'] = player_container_ref

            with splitter.after:
                with ui.tabs().classes('w-full mb-2') as tabs:
                    tab_videom = ui.tab('Filmdata', icon='edit_note')
                    tab_clipmaker = ui.tab('Clipper', icon='movie_creation')
                with ui.tab_panels(tabs, value=tab_videom).classes('w-full h-full'):
                    with ui.tab_panel(tab_videom):
                        with ui.column().classes('w-full gap-4 p-2'):
                            chips_input_ref, chips_list, chips_error, chips_container = chips_input_combined(
                                [f'@{p}' for p in video.get('partners', [])] + [f'#{l}' for l in video.get('labels', [])]
                            )
                            notes_input = ui.textarea('Notes', value=video.get('notes', '')).props('rows=6').classes('w-full')

                            def rerender_chips():
                                chips_container.clear()
                                for val in chips_list:
                                    ui.chip(
                                        val,
                                        icon='person' if val.startswith('@') else 'label',
                                        color='secondary' if val.startswith('@') else 'primary',
                                        removable=True
                                    ).on('remove', lambda e, v=val: (chips_list.remove(v), rerender_chips()))

                            def reset_metadata_fields():
                                # Reset chips and notes to original video values
                                chips_list.clear()
                                chips_list.extend([f'@{p}' for p in video.get('partners', [])] + [f'#{l}' for l in video.get('labels', [])])
                                notes_input.value = video.get('notes', '')
                                rerender_chips()

                            with ui.row().classes('justify-start gap-2 mt-2'):
                                ui.button(
                                    "💾 Save",
                                    on_click=lambda: handle_publish(
                                        video_metadata={
                                            "partners": [c[1:] for c in chips_list if c.startswith('@')],
                                            "labels": [c[1:] for c in chips_list if c.startswith('#')],
                                            "notes": notes_input.value,
                                        }
                                    )
                                ).props('color=primary')
                                ui.button("Cancel", on_click=reset_metadata_fields).props('color=secondary')
                    with ui.tab_panel(tab_clipmaker):
                        with ui.column().classes('w-full gap-4 p-2'):
                            clip_form_container['container'] = ui.column().classes('w-full gap-2')
                            clip_id = str(uuid.uuid4())[:8]
                            funny_title = generate_funny_title()
                            show_clip_form(
                                clip_form_state.get('clip') or {
                                    'clip_id': clip_id,
                                    'title': funny_title,
                                    'start': 0,
                                    'end': 0,
                                    'description': '',
                                    'labels': [],
                                    'partners': [],
                                },
                                is_new=clip_form_state.get('is_new', True)
                            )
            with splitter.separator:
                ui.icon('drag_indicator').classes('text-gray-400')

        # Clipboard heading with count
        video = load_video(video_id)
        clips = video.get("clips", [])
        ui.label(f'📋 Clipboard ({len(clips)})').classes('text-xl font-semibold mt-4')
        with ui.grid(columns=5).classes('w-full gap-4 mb-8') as clipboard_container:
            refresh_clipboard()

        ui.separator()
        # Filmboard heading with count
        all_videos = load_videos()
        current_video_date = video.get('date', '').split('T')[0]
        same_day_videos = [v for v in all_videos if v.get('date', '').startswith(current_video_date) and v['video_id'] != video_id]
        ui.label(f'🎥 Filmboard ({len(same_day_videos) + 1})').classes('text-xl font-semibold mt-8')
        with ui.grid(columns=5).classes('w-full gap-4 mb-8') as filmboard_container:
            refresh_filmboard()

    player_container['ref'] = player_container_ref
    player_container['textarea'] = None

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

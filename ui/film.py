# film.py
from nicegui import ui, app
from dialog_puns import caught_john_doe
from video_player import VideoPlayer
from utils_api import convert_video_metadata_to_raw_text, load_video, parse_and_save_clips, convert_clips_to_raw_text, parse_raw_text, load_videos, parse_video_metadata, save_video_metadata
from utils_api import add_clip_to_video, update_clip_in_video, get_playlist_id_for_video
from utils import format_time
from films import navigate_to_film
import random
import re
import uuid

#TODO: Populate demo videos to demo playlist
DEMO_VIDEO_POOL = [
    {"video_id": "Wv1cAFUIJzw", "title": "Demo Grappling Breakdown", "duration_seconds": 300},
]


def film_page(video_id: str):
    player_container = {'ref': None}
    demo_mode = False
    if video_id == "demo":
        demo_mode = True
    # Load actual video from DB or demo stub
    if demo_mode:
        selected = next((v for v in DEMO_VIDEO_POOL if v['video_id'] == video_id), None)
        video = selected or random.choice(DEMO_VIDEO_POOL)
        video_id = video['video_id']
    video = load_video(video_id)
    if not video:
        ui.label(f"⚠️ Video: {video_id} not found!")
        return
    # raw_text = convert_clips_to_raw_text(video_id, video['duration_seconds'])

    # # Initialize session-backed draft text
    # session_key = f"clip_draft_{video_id}"
    # if not app.storage.user.get(session_key):
    #     app.storage.user[session_key] = raw_text

    # State to track which clip is being edited (or None for new)
    clip_form_state = {'clip': None, 'is_new': True}
    clip_form_container = {}

    def add_clip():
        # Generate a unique id for the new clip
        clip_id = str(uuid.uuid4())  # or [:8] for short
        empty_clip = {
            'clip_id': clip_id,
            'title': f'clip-{clip_id[:8]}',
            'start': 0,
            'end': 0,
            'description': '',
            'labels': [],
            'partners': [],
        }
        show_clip_form(empty_clip, is_new=True)

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
                title = ui.input('Title', value=clip.get('title', '')).classes('w-full')

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

                # --- Raw text section ---
                raw_text_value = clip_to_raw_text(clip)
                raw_text = ui.textarea(
                    'Metadata',
                    value=raw_text_value
                ).props('rows=4').classes('w-full')

                with ui.row().classes('justify-end gap-2 mt-4'):
                    def save_clip():
                        parsed = raw_text_to_clip(raw_text.value)
                        updated_clip = {
                            'clip_id': clip.get('clip_id'),
                            'title': title.value,
                            'start': hms_to_seconds(start_input.value),
                            'end': hms_to_seconds(end_input.value),
                            'description': parsed['description'],
                            'labels': parsed['labels'],
                            'partners': parsed['partners'],
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
                        clip_form_state['clip'] = {
                            'clip_id': clip_id,
                            'title': f'clip-{clip_id[:8]}',
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

    def on_add_clip():
        # Generate a unique id for the new clip
        clip_id = str(uuid.uuid4())
        clip_form_state['clip'] = {
            'clip_id': clip_id,
            'title': f'clip-{clip_id[:8]}',
            'start': 0,
            'end': 0,
            'description': '',
            'labels': [],
            'partners': [],
        }
        clip_form_state['is_new'] = True
        show_clip_form(clip_form_state['clip'], is_new=True)

    def on_edit_clip(clip):
        clip_form_state['clip'] = clip
        clip_form_state['is_new'] = False
        show_clip_form(clip, is_new=False)

    def play_clip(clip):
        ui.notify(f"▶️ Playing: {clip['title']}", type="info")
        start_time = clip.get("start", 0)
        ref = player_container['ref']
        if ref:
            ref.clear()
            with ref:
                VideoPlayer(video_id, start=start_time, end=clip.get("end"))

    def add_clip_card(clip):
        with ui.card().classes('p-2 flex flex-col justify-between'):
            with ui.column().classes('w-full gap-2'):
                ui.label(clip["title"]).classes('font-medium text-sm truncate')
                start_time = format_time(clip.get('start', 0))
                end_time = format_time(clip.get('end', 0))
                ui.label(f"⏱ {start_time} - {end_time}").classes('text-xs text-gray-500')
            with ui.row().classes('justify-end gap-2 mt-2'):
                ui.button(icon='play_arrow', on_click=lambda: play_clip(clip)).props('flat color=primary').tooltip('Play')
                ui.button(icon='edit', on_click=lambda: on_edit_clip(clip)).props('flat color=secondary').tooltip('Edit')

    def refresh_clipboard():
        clipboard_container.clear()
        with clipboard_container:
            # Existing clips
            video = load_video(video_id)
            clips = video.get("clips", [])
            for clip in clips:
                add_clip_card(clip)

    def handle_publish(textarea):
        token = app.storage.user.get("token")
        if not token:
            caught_john_doe()
            return
        try:
            video_metadata = parse_video_metadata(textarea.value)
            # Merge with required fields from the loaded video
            for key in ["video_id", "youtube_url", "title", "date", "duration_seconds"]:
                video_metadata[key] = video.get(key)
            # 🛑 Preserve existing clips!
            video_metadata["clips"] = video.get("clips", [])
            success = save_video_metadata(video_metadata, token)
            if success:
                ui.notify("✅ Video metadata published", type="positive")
            else:
                ui.notify("❌ Failed to publish metadata", type="negative")
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
                ui.label("📭 No other videos found from the same day.").classes('text-sm text-gray-500')
                return

            # Display thumbnails for videos from the same day
            for v in same_day_videos:
                with ui.card().classes('cursor-pointer hover:shadow-lg p-2').on('click', lambda e, vid=v['video_id']: navigate_to_film(vid, e)):
                    with ui.column().classes('w-full gap-2'):
                        # Thumbnail
                        thumbnail_url = f'https://img.youtube.com/vi/{v["video_id"]}/0.jpg'
                        ui.image(thumbnail_url).classes('w-full rounded aspect-video object-cover')
                        # Title
                        ui.label(v["title"]).classes('font-medium text-sm truncate')
                        # Duration
                        ui.label(f"⏱ {format_time(v.get('duration_seconds', 0))}").classes('text-xs text-gray-500')

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
                    VideoPlayer(video_id)
                player_container['ref'] = player_container_ref

            with splitter.after:
                with ui.tabs().classes('w-full') as tabs:
                    tab_clipmaker = ui.tab('Clip Maker', icon='movie_creation')
                    tab_clipper = ui.tab('Video Metadata', icon='edit_note')
                with ui.tab_panels(tabs, value=tab_clipmaker).classes('w-full h-full'):
                    with ui.tab_panel(tab_clipmaker):
                        with ui.column().classes('w-full'):
                            # Dedicated container for the Clip Maker form
                            clip_form_container['container'] = ui.column().classes('w-full')
                            clip_id = str(uuid.uuid4())[:8]
                            show_clip_form(
                                clip_form_state.get('clip') or {
                                    'clip_id': clip_id,
                                    'title': f'clip-{clip_id[:8]}',
                                    'start': 0,
                                    'end': 0,
                                    'description': '',
                                    'labels': [],
                                    'partners': [],
                                },
                                is_new=clip_form_state.get('is_new', True)
                            )
                    with ui.tab_panel(tab_clipper):
                        textarea = ui.textarea(
                            '✏️ Video Metadata',
                            value=convert_video_metadata_to_raw_text(video)
                        ).props('rows=12').classes('w-full h-[45vh]')
                        with ui.row().classes('justify-start gap-2 mt-2'):
                            ui.button("💾 Save", on_click=lambda: handle_publish(textarea)).props('color=primary')
                            ui.button("🧹 Clear", on_click=caught_john_doe).props('color=warning')
                            # if not demo_mode:
                            #     ui.button("🚀 Publish", on_click=lambda: handle_publish(textarea)).props('color=primary')


            with splitter.separator:
                ui.icon('drag_indicator').classes('text-gray-400')

        ui.label('📋 Clipboard').classes('text-xl font-semibold mt-4')
        with ui.grid(columns=5).classes('w-full gap-4') as clipboard_container:
            refresh_clipboard()

        # Filmboard Section
        ui.label('🎥 Filmboard: Videos from the Same Day').classes('text-xl font-semibold mt-8')
        with ui.grid(columns=5).classes('w-full gap-4') as filmboard_container:
            refresh_filmboard()

    player_container['ref'] = player_container_ref
    player_container['textarea'] = textarea


# --- Helper functions for raw text <-> clip dict ---

def clip_to_raw_text(clip):
    """Convert a clip dict to raw text format, using space as delimiter for @ and #."""
    partners_line = ' '.join(f'@{p}' for p in clip.get('partners', [])) if clip.get('partners') else ''
    labels_line = ' '.join(f'#{l}' for l in clip.get('labels', [])) if clip.get('labels') else ''
    notes_lines = clip.get('description', '')
    return '\n'.join(filter(None, [partners_line, labels_line, notes_lines]))

def raw_text_to_clip(text):
    """Parse raw text into a clip dict. @ and # can be anywhere, space-delimited, rest is notes."""
    partners, labels = [], []
    notes_lines = []
    for line in text.strip().split('\n'):
        # Find all @partners and #labels in the line, space-delimited
        found_partners = re.findall(r'@(\w+)', line)
        found_labels = re.findall(r'#(\w+)', line)
        partners.extend(found_partners)
        labels.extend(found_labels)
        # Remove @... and #... tokens from the line for notes
        cleaned = re.sub(r'[@#]\w+', '', line).strip()
        if cleaned:
            notes_lines.append(cleaned)
    return {
        'partners': partners,
        'labels': labels,
        'description': '\n'.join(notes_lines).strip(),
    }

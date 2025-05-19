# film.py
from nicegui import ui, app
from video_player import VideoPlayer
from utils_api import load_video, parse_and_save_clips, convert_clips_to_raw_text, parse_raw_text, load_videos
from utils import format_time
from films import navigate_to_film
import random

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
    raw_text = convert_clips_to_raw_text(video_id, video['duration_seconds'])

    # Initialize session-backed draft text
    session_key = f"clip_draft_{video_id}"
    if not app.storage.user.get(session_key):
        app.storage.user[session_key] = raw_text

    def refresh_clipboard():
        clipboard_container.clear()
        with clipboard_container:
            draft_text = app.storage.user.get(session_key, "")
            try:
                parsed = parse_raw_text(draft_text)
                clips = parsed.get("clips", [])
                for clip in clips:
                    add_clip_card(clip)
            except Exception as e:
                ui.notify(f"❌ Error parsing clipboard: {e}", type="negative")

    def handle_clear_local_changes():
        app.storage.user[session_key] = raw_text  # Reset to DB/default version
        textarea.value = raw_text  # Update editor
        ui.notify("🧹 Local changes cleared")
        refresh_clipboard()

    def handle_local_save(textarea):
        app.storage.user[session_key] = textarea.value
        ui.notify("✅ Draft saved locally")
        refresh_clipboard()

    def handle_publish(textarea):
        token = app.storage.user.get("token")
        if not token:
            ui.notify("🔒 Login required to publish changes", type="warning")
            return
        try:
            success = parse_and_save_clips(video_id, textarea.value, token)
            if success:
                ui.notify("✅ Published to database", type="positive")
                refresh_clipboard()
            else:
                ui.notify("❌ Failed to publish", type="negative")
        except Exception as e:
            ui.notify(f"❌ Error: {e}", type="negative")
    
    def play_clip(clip):
        ui.notify(f"▶️ Playing: {clip['title']}", type="info")
        start_time = clip.get("start", 0)
        ref = player_container['ref']
        if ref:
            ref.clear()
            with ref:
                VideoPlayer(video_id, start=start_time)

    def add_clip_card(clip):
        with ui.card().classes('cursor-pointer hover:shadow-lg p-2').on('click', lambda e: play_clip(clip)):
            with ui.column().classes('w-full gap-2'):
                # Display the clip title
                ui.label(clip["title"]).classes('font-medium text-sm truncate')
                # Display the clip start and end times in a human-readable format
                start_time = format_time(clip.get('start', 0))
                end_time = format_time(clip.get('end', 0))
                ui.label(f"⏱ {start_time} - {end_time}").classes('text-xs text-gray-500')

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
            if prev_video:
                with ui.row().classes('items-center cursor-pointer').on('click', lambda e: navigate_to_film(prev_video['video_id'], e)):
                    ui.icon('arrow_back').classes('text-blue-500')
                    ui.label(f"Previous: {prev_video['title']}").classes('text-sm text-blue-500 truncate')
            else:
                ui.space()  # Add space if no previous video

            if next_video:
                with ui.row().classes('items-center cursor-pointer').on('click', lambda e: navigate_to_film(next_video['video_id'], e)):
                    ui.label(f"Next: {next_video['title']}").classes('text-sm text-blue-500 truncate')
                    ui.icon('arrow_forward').classes('text-blue-500')
            else:
                ui.space()  # Add space if no next video

        ui.label(f'🎬 Studying: {video.get("title", "Untitled Video")}').classes('text-2xl font-bold')

        player_container_ref = None

        with ui.splitter(horizontal=False, value=70).classes('w-full h-[70vh] rounded shadow') as splitter:
            with splitter.before:
                with ui.column().classes('w-full h-full p-4 gap-4') as player_container_ref:
                    VideoPlayer(video_id)
                player_container['ref'] = player_container_ref

            with splitter.after:
                with ui.column().classes('w-full h-full p-2 gap-4'):
                    # Set a larger default height for the textarea
                    textarea = ui.textarea(
                        '✏️ Clipper',
                        value=app.storage.user[session_key]
                    ).props('rows=15').classes('w-full h-full')

                    # Add a row for buttons below the textarea
                    with ui.row().classes('justify-start gap-2 mt-2'):
                        ui.button("💾 Save", on_click=lambda: handle_local_save(textarea)).props('color=primary')
                        ui.button("🧹 Clear", on_click=handle_clear_local_changes).props('color=warning')
                        if not demo_mode:
                            ui.button("🚀 Publish", on_click=lambda: handle_publish(textarea)).props('color=primary')
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

# film.py
from nicegui import ui, app
from video_player import VideoPlayer
from utils_api import load_video, parse_and_save_clips, convert_clips_to_raw_text, parse_raw_text
from utils import format_time
import random

# Optional demo video pool
DEMO_VIDEO_POOL = [
    {"video_id": "Wv1cAFUIJzw", "title": "Demo Grappling Breakdown", "duration_seconds": 300},
]

# @ui.page('/film/{video_id}')
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
        with ui.card().classes('cursor-pointer hover:shadow-lg').on('click', lambda e: play_clip(clip)):
            thumbnail_url = f'https://img.youtube.com/vi/{video_id}/0.jpg'
            ui.image(thumbnail_url).classes('w-full rounded')
            ui.label(clip["title"]).classes('font-medium mt-2')

    # Inline render_film_editor functionality
    with ui.column().classes('w-full p-4 gap-6'):

        ui.label(f'🎬 Editing: {video.get("title", "Untitled Video")}').classes('text-2xl font-bold')

        player_container_ref = None

        with ui.splitter(horizontal=False, value=70).classes('w-full h-[70vh] rounded shadow') as splitter:
            with splitter.before:
                with ui.column().classes('w-full h-full p-2 gap-2') as player_container_ref:
                    VideoPlayer(video_id)
                player_container['ref'] = player_container_ref


            with splitter.after:
                with ui.column().classes('w-full h-full p-2 gap-4'):
                    textarea = ui.textarea('✏️ Clipper', value=app.storage.user[session_key]).classes('w-full h-[calc(100%-3rem)]')
                    with ui.row():
                        ui.button("💾 Save", on_click=lambda: handle_local_save(textarea)).props('color=primary')
                        ui.button("🧹 Clear", on_click=handle_clear_local_changes).props('color=warning')
                        if not demo_mode:
                            ui.button("🚀 Publish", on_click=lambda: handle_publish(textarea)).props('color=primary')
            with splitter.separator:
                ui.icon('drag_indicator').classes('text-gray-400')

        ui.label('📋 Clipboard').classes('text-xl font-semibold mt-4')

        with ui.grid(columns=5).classes('w-full gap-4') as clipboard_container:
            refresh_clipboard()

    player_container['ref'] = player_container_ref
    player_container['textarea'] = textarea

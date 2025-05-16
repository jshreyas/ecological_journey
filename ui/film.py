from nicegui import ui, app
from video_player import VideoPlayer
from utils_api import load_video, parse_and_save_clips, convert_clips_to_raw_text
from shared_film_editor import render_film_editor

@ui.page('/film/{video_id}')
def film_page(video_id: str):
    video = load_video(video_id)
    if not video:
        ui.label(f"⚠️ Video: {video_id} not found!")
        return

    raw_text = convert_clips_to_raw_text(video_id, video["duration_seconds"])

    def handle_save(textarea):
        try:
            success = parse_and_save_clips(video_id, textarea.value, app.storage.user.get('token'))
            if success:
                ui.notify('✅ Clips saved', type='positive')
            else:
                ui.notify('❌ Error', type='negative')
        except Exception as e:
            ui.notify(f"❌ Error: {e}", type='negative')

    def play_clip(clip):
        start_time = clip.get("start", 0)
        ref = player_container['ref']
        ref.clear()
        with ref:
            VideoPlayer(video_id, start=start_time)

    player_container = render_film_editor(video, video_id, raw_text, handle_save, play_clip)

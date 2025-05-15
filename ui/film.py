from nicegui import ui, app
from video_player import VideoPlayer
from utils_api import load_video, parse_and_save_clips, convert_clips_to_raw_text


@ui.page('/film/{video_id}')
def film_page(video_id: str):
    video = load_video(video_id)
    if not video:
        ui.label(f"⚠️ Video: {video_id} not found!")
        return

    raw_text = convert_clips_to_raw_text(video_id, video["duration_seconds"])

    with ui.column().classes('w-full p-4 gap-6'):

        # 🎬 Title
        ui.label(f'🎬 Editing: {video.get("title", "Untitled Video")}').classes('text-2xl font-bold')

        # ✨ Player container reference (declared inline in layout)
        player_container = None  # will be assigned after declaration

        # Section 1: Vertical Splitter (Video / Editor)
        with ui.splitter(horizontal=False, value=70).classes('w-full h-[70vh] rounded shadow') as splitter:
            with splitter.before:
                # 🔼 Top: Video Player
                with ui.column().classes('w-full h-full p-2 gap-2') as player_container_ref:
                    VideoPlayer(video_id)

                # Assign to outer scope
                nonlocal_player_container = {'ref': None}
                nonlocal_player_container['ref'] = player_container_ref

            with splitter.after:
                # 🔽 Bottom: Clipper Textarea
                with ui.column().classes('w-full h-full p-2 gap-4'):
                    textarea = ui.textarea('✏️ Clipper', value=raw_text).classes('w-full h-[calc(100%-3rem)]')
                    ui.button("💾 Save Changes", on_click=lambda: handle_save(textarea, video_id)).props('color=primary')

            with splitter.separator:
                ui.icon('drag_indicator').classes('text-gray-400')

        # Section 2: Clips Grid
        ui.label('📋 Clipboard').classes('text-xl font-semibold mt-4')

        with ui.grid(columns=5).classes('w-full gap-4'):
            for clip in video["clips"]:
                with ui.card().classes('cursor-pointer hover:shadow-lg').on('click', lambda e, c=clip: play_clip(c)):
                    thumbnail_url = f'https://img.youtube.com/vi/{video_id}/0.jpg'
                    ui.image(thumbnail_url).classes('w-full rounded')
                    ui.label(clip["title"]).classes('font-medium mt-2')

    # Play selected clip (replaces video player with clip start time)
    def play_clip(clip):
        start_time = clip.get("start", 0)
        ref = nonlocal_player_container['ref']
        ref.clear()
        with ref:
            VideoPlayer(video_id, start=start_time)

    # Save clip edits
    def handle_save(textarea, video_id):
        try:
            success = parse_and_save_clips(video_id, textarea.value, app.storage.user.get('token'))
            if success:
                ui.notify('✅ Clips saved', type='positive')
            else:
                ui.notify('❌ Error', type='negative')
        except Exception as e:
            ui.notify(f"❌ Error: {e}", type='negative')

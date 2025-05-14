from nicegui import ui, app
from utils_api import load_videos, load_clips, parse_and_save_clips, convert_clips_to_raw_text
from utils import format_time, embed_youtube_player
import math


@ui.page("/video_reviewer")
def video_reviewer():

    ui.label("⚠️ TODO: Make this a demo/playarea for non-users!")
    return

    video_options = {f"{v['title']} ({v['video_id']})": v["video_id"] for v in videos}
    video_keys = list(video_options.keys())
    selected_video_key = video_keys[0]
    selected_video_id = video_options[selected_video_key]

    # Main container that gets cleared on dropdown video selection
    content_container = ui.column().classes('w-full')

    def update_page_for_video(video_id: str):
        content_container.clear()

        selected_video = next((v for v in videos if v["video_id"] == video_id), None)
        if not selected_video:
            ui.notify("Video not found", type="warning")
            return

        segments = load_clips(video_id)

        with content_container:
            with ui.splitter(horizontal=False, value=80).classes('w-full mt-4') as splitter:

                # ✅ Declare player container outside so we can reuse it
                player_container = ui.column().classes('w-full mt-4')

                with splitter.before:
                    player_container.clear()  # Clear in case of reload
                    with player_container:
                        embed_youtube_player(video_id, start=0, end=None)

                with splitter.after:
                    editor_container = ui.column().classes('w-full gap-2')

                    raw_text = convert_clips_to_raw_text(video_id, selected_video["duration_seconds"])
                    textarea = ui.textarea('✏️ Clipper', value=raw_text).classes('w-full h-64')

                    def save_changes():
                        try:
                            parse_and_save_clips(video_id, textarea.value)
                            ui.notify('Clips saved', type='positive')
                            ui.run_javascript('location.reload()')
                        except Exception as e:
                            ui.notify(f"Error: {e}", type='negative')

                    ui.button("💾 Save Changes", on_click=save_changes).props('color=primary')

                with splitter.separator:
                    ui.icon('filter_alt').classes('text-blue')

            # Clipboard section
            ui.markdown("## 🎞️ Clipboard")
            clip_buttons = [seg for seg in segments if seg["type"] == "clip"]
            if not clip_buttons:
                ui.label("⚠️ No clips found for the video!")
                return

            NUM_COLUMNS = 3
            num_rows = math.ceil(len(clip_buttons) / NUM_COLUMNS)

            for row in range(num_rows):
                with ui.row().classes('w-full'):
                    for col_idx in range(NUM_COLUMNS):
                        i = row * NUM_COLUMNS + col_idx
                        if i < len(clip_buttons):
                            seg = clip_buttons[i]
                            is_selected = i == state.selected_segment_idx
                            label = f"{seg['title']} ({format_time(seg['start'])} → {format_time(seg['end'])})"
                            if is_selected:
                                label = f"⭐ {label}"

                            # ✅ Proper closure to reuse player_container
                            def make_click_fn(idx, seg=seg, player_container=player_container):
                                def click_fn():
                                    state.selected_segment_idx = idx
                                    player_container.clear()
                                    embed_youtube_player(video_id, start=seg["start"], end=seg["end"])
                                return click_fn

                            ui.button(label, on_click=make_click_fn(i, seg, player_container))

    # Dropdown selector
    def on_video_select(e):
        selected_id = video_options[e.value]
        update_page_for_video(selected_id)

    ui.select(video_keys, on_change=on_video_select, label='Choose a video', value=selected_video_key)

    # Initial render
    update_page_for_video(selected_video_id)

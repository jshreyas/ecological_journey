from nicegui import ui
from utils import format_time
from dialog_puns import in_progress
from utils_api import load_cliplist, load_clips
from video_player import VideoPlayer

# ---- Global State ----
current_index = 0
is_autoplay = True
is_loop = True

queue_buttons = []
queue = []


def playcliplist_page(cliplist_id):

    if not cliplist_id:
        in_progress()
        return
    global current_index, queue_buttons, queue

    all_videos = load_clips()
    cliplist = load_cliplist(cliplist_id)
    filters_to_use = cliplist.get('filters', {})

    filtered_videos = [
        v for v in all_videos
        if v['playlist_name'] in filters_to_use.get('playlists', [])
        and (not filters_to_use.get('labels') or any(label in v.get('labels', []) for label in filters_to_use.get('labels', [])))
        and (not filters_to_use.get('partners') or any(partner in v.get('partners', []) for partner in filters_to_use.get('partners', [])))
    ]

    queue = filtered_videos.copy()
    queue_buttons = []
    current_index = 0
    if not queue:
        ui.notify("No clips found for selected filters", type='warning')
        return

    def play_clip(index: int):
        global current_index
        current_index = index
        highlight_queue()

        player_column.clear()
        with player_column:
            VideoPlayer(
                video_url=queue[index]['video_id'],
                start=queue[index]['start'],
                end=queue[index]['end'],
                speed=2.0, #TODO: pick from clip, else default to 2.0
                on_end=lambda: next_clip() if is_autoplay else None,
                parent=player_column  # ✅ key fix
            )

    def next_clip():
        global current_index
        current_index = (current_index + 1) % len(queue)
        play_clip(current_index)

    def highlight_queue():
        for i, btn in enumerate(queue_buttons):
            btn.props('color=secondary' if i == current_index else 'color=primary')

    def render_clip_card(clip, index):
        title = clip.get('title') or f"Clip {index + 1}"
        partners = ', '.join(clip.get('partners', []))
        labels = ', '.join(clip.get('labels', []))
        start_time = format_time(clip.get('start', 0))
        end_time = format_time(clip.get('end', 0))
                
        card_classes = 'bg-secondary text-white' if index == current_index else 'bg-white text-black'
        card_tailwind = f'{card_classes} p-3 rounded-lg shadow-md hover:shadow-lg'

        card = ui.card().classes(
            'w-full mb-2 transition-all duration-200 ease-in-out cursor-pointer'
        )
        with card:
            col = ui.column().classes(card_tailwind).on('click', lambda idx=index: play_clip(idx))
            with col:
                ui.label(title).classes('text-md font-semibold')
                with ui.row().classes('w-full gap-2 justify-between'):
                    ui.label(f"⏱ {start_time} - {end_time}").classes('text-xs')
                    ui.label(f"{format_time(clip.get('end', 0) - clip.get('start', 0))}").classes('text-xs')

                if partners:
                    ui.label(f"👥 {partners}").classes('text-sm opacity-80')
                if labels:
                    ui.label(f"🏷️ {labels}").classes('text-sm opacity-60')
        return card

    # --- Layout ---
    with ui.splitter(value=70, horizontal=False).classes('w-full h-full') as splitter:
        with splitter.before:
            player_column = ui.column().classes('w-full h-full').style('height: 100%; height: 56.25vw; max-height: 70vh;')
        with splitter.after:
            with ui.scroll_area().classes('w-full h-full p-2').style('height: 100%; height: 56.25vw; max-height: 70vh;'):
                for i, clip in enumerate(queue):
                    queue_buttons.append(render_clip_card(clip, i))

    # Start
    play_clip(current_index)
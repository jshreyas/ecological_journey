from nicegui import ui
import random
from utils_api import load_cliplist, load_clips
from video_player import VideoPlayer

# ---- Global State ----
current_index = 0
is_autoplay = True
is_loop = True
is_shuffle = False

queue_buttons = []
queue = []

player_container = ui.column()  # ensure it’s initialized early

def playcliplist_page():

    global current_index, queue_buttons, queue

    all_videos = load_clips()
    all_playlists = sorted(list({v['playlist_name'] for v in all_videos}))

    cliplist_id = "4757a82b-b79d-494e-af2b-27e01384d7a8"
    cliplist = load_cliplist(cliplist_id)
    cliplist_filter_override = {
        'clip_ids': set(cliplist['clip_ids']),
        'filters': cliplist.get('filters', {})
    }

    filters_to_use = cliplist_filter_override['filters']
    filtered_videos = [
        v for v in all_videos
        if v['playlist_name'] in filters_to_use.get('playlists', [])
        and (not filters_to_use.get('labels') or any(label in v.get('labels', []) for label in filters_to_use['labels']))
        and (not filters_to_use.get('partners') or any(partner in v.get('partners', []) for partner in filters_to_use['partners']))
    ]

    queue = filtered_videos.copy()
    queue_buttons = []

    if not queue:
        ui.notify("No videos found for this cliplist and filters", type='warning')
        return

    # --- Core Functions ---
    def play_clip(index: int):
        global current_index
        current_index = index
        highlight_queue()

        player_container.clear()
        with player_container:
            print(f"Playing clip {index + 1}/{len(queue)}: {queue[index].get('title', 'Unknown Title')}")
            print(f"Video ID: {queue[index]['video_id']}, Start: {queue[index]['start']}, End: {queue[index]['end']}")
            VideoPlayer(
                video_url=queue[index]['video_id'],
                start=queue[index]['start'],
                end=queue[index]['end'],
                speed=2.0,
                on_end=lambda: next_clip() if is_autoplay else None,
            )

    def next_clip():
        global current_index
        if is_shuffle:
            current_index = random.randint(0, len(queue) - 1)
        else:
            current_index += 1
            if current_index >= len(queue):
                if is_loop:
                    current_index = 0
                else:
                    return
        play_clip(current_index)

    def highlight_queue():
        for i, button in enumerate(queue_buttons):
            button.props('color=secondary' if i == current_index else 'color=primary')

    # --- Layout ---
    with ui.splitter(horizontal=False, value=70).classes('w-full') as splitter:
        with splitter.before:
            with player_container:
                # initial empty container; real video loads later
                ui.label('Loading clip...')

        with splitter.after:
            for i, clip in enumerate(queue):
                title = clip.get('title') or f"clip-{i+1}"
                btn = ui.button(title, on_click=lambda i=i: play_clip(i)).classes('w-full justify-start')
                queue_buttons.append(btn)

    # --- Playback Controls ---
    with ui.row().classes('mt-4'):
        ui.checkbox('Autoplay', value=is_autoplay,
                    on_change=lambda e: globals().__setitem__('is_autoplay', e.value))
        ui.checkbox('Loop', value=is_loop,
                    on_change=lambda e: globals().__setitem__('is_loop', e.value))
        ui.checkbox('Shuffle', value=is_shuffle,
                    on_change=lambda e: globals().__setitem__('is_shuffle', e.value))

    # --- Start Playing ---
    play_clip(current_index)

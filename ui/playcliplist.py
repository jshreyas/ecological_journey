from nicegui import ui
import random
from utils_api import load_cliplist, load_clips
from video_player import VideoPlayer


# cliplist = [
#     {'video_id': 'O96S4glZKrQ', 'start': 81, 'end': 162, 'title': 'bouncy-lobster'},
#     {'video_id': 'aaQT6nn9m-o', 'start': 90, 'end': 130, 'title': 'clip-80a333e5'},
#     {'video_id': 'lUW9R9xdGhQ', 'start': 200, 'end': 221, 'title': 'clip-5e66812a'},
#     {'video_id': 'lUW9R9xdGhQ', 'start': 249, 'end': 335, 'title': 'clip-cf8df59d'},
# ]

current_index = 0
is_autoplay = True
is_loop = True
is_shuffle = False

queue_buttons = []
player_container = None  # will be assigned in layout later

all_videos = load_clips()
all_playlists = sorted(list({v['playlist_name'] for v in all_videos}))

cliplist_id = "0116d8b6-3bc9-4f46-862f-ae7863aced88"
cliplist_id = "4757a82b-b79d-494e-af2b-27e01384d7a8"
cliplist = load_cliplist(cliplist_id)
cliplist_filter_override = {
    'clip_ids': set(cliplist['clip_ids']),
    'filters': cliplist.get('filters', {})
}
print(f"cliplist_filter_override: {cliplist_filter_override}")

filters_to_use = cliplist_filter_override['filters']

filtered_videos = [
    v for v in all_videos
    if v['playlist_name'] in filters_to_use['playlists']
    and (not filters_to_use['labels'] or any(label in v.get('labels', []) for label in filters_to_use['labels']))
    and (not filters_to_use['partners'] or any(partner in v.get('partners', []) for partner in filters_to_use['partners']))
]
print(f"filtered_videos: {filtered_videos}")

queue = filtered_videos.copy()

def playcliplist_page():

    # import pdb; pdb.set_trace()
    def play_clip(index: int):
        global current_index, player_container
        current_index = index
        highlight_queue()

        if player_container is not None:
            player_container.clear()
            with player_container:
                VideoPlayer(
                    video_url=f"https://www.youtube.com/watch?v={queue[index]['video_id']}",
                    start=queue[index]['start'],
                    end=queue[index]['end'],
                    speed=1.0,
                    on_end=next_clip if is_autoplay else None,
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
            if i == current_index:
                button.props('color="primary"')
            else:
                button.props('color="white"')

    # --- Layout ---
    with ui.splitter(value=20).props('horizontal') as splitter:
        with splitter.before:
            player_container = ui.column()
        with splitter.after:
            ui.label('Clip Queue')
            for i, clip in enumerate(queue):
                btn = ui.button(clip['title'], on_click=lambda i=i: play_clip(i))
                queue_buttons.append(btn)

    # --- Playback Controls ---
    with ui.row().classes('mt-4'):
        ui.checkbox('Autoplay', value=is_autoplay,
                    on_change=lambda e: globals().__setitem__('is_autoplay', e.value))
        ui.checkbox('Loop', value=is_loop,
                    on_change=lambda e: globals().__setitem__('is_loop', e.value))
        ui.checkbox('Shuffle', value=is_shuffle,
                    on_change=lambda e: globals().__setitem__('is_shuffle', e.value))

    play_clip(current_index)
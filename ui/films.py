from nicegui import ui
from utils_api import load_videos
import datetime
from collections import Counter
from functools import partial

def navigate_to_film(video_id, e):
    ui.navigate.to(f'/film/{video_id}')


def films_page():
    ui.label("🤼 Films, Films, and more Films!").classes('text-2xl font-bold mb-4')

    videos = load_videos()

    videos_sorted = sorted(videos, key=lambda x: x['date'], reverse=True)[:80]
    with ui.grid(columns=5).classes('w-full gap-0'):
        for v in videos_sorted:
            with ui.card().classes('cursor-pointer hover:shadow-xl').on('click', partial(navigate_to_film, v["video_id"])):
                thumbnail_url = f'https://img.youtube.com/vi/{v["video_id"]}/0.jpg'
                ui.image(thumbnail_url).classes('w-full rounded')
                ui.label(v["title"]).classes('font-medium mt-2')
                ui.label(f"📅 {v['date'][:10]}").classes('text-sm text-gray-500')

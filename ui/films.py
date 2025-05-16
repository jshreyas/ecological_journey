from nicegui import ui
from utils_api import load_videos
from functools import partial

VIDEOS_PER_PAGE = 12

def navigate_to_film(video_id, e):
    ui.navigate.to(f'/film/{video_id}')

def films_page():
    current_page = {'value': 1}
    ui.label("🤼 Films, Films, and more Films!") \
        .classes('text-2xl font-bold mb-4 text-center')

    videos = load_videos()
    videos_sorted = sorted(videos, key=lambda x: x['date'], reverse=True)[:80]
    total_pages = (len(videos_sorted) + VIDEOS_PER_PAGE - 1) // VIDEOS_PER_PAGE

    def render_page():
        start = (current_page['value'] - 1) * VIDEOS_PER_PAGE
        end = start + VIDEOS_PER_PAGE
        paginated_videos = videos_sorted[start:end]

        video_grid.clear()
        with video_grid:
            for v in paginated_videos:
                with ui.card().classes(
                    'cursor-pointer hover:shadow-xl transition-shadow duration-200'
                ).on('click', partial(navigate_to_film, v["video_id"])):
                    thumbnail_url = f'https://img.youtube.com/vi/{v["video_id"]}/0.jpg'
                    ui.image(thumbnail_url).classes('w-full rounded aspect-video object-cover')
                    ui.label(v["title"]) \
                        .tooltip(v["title"]) \
                        .classes('font-medium mt-2 truncate text-sm sm:text-base')
                    ui.label(f"📅 {v['date'][:10]}") \
                        .classes('text-sm text-gray-500')

    # Responsive grid container
    video_grid = ui.grid().classes(
        'grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 w-full'
    )

    render_page()

    def on_page_change(e):
        current_page['value'] = pagination.value
        render_page()

    pagination = ui.pagination(
        min=1,
        max=total_pages,
        value=current_page,
        on_change=on_page_change,
        direction_links=True  # optional if you want prev/next arrows
    ) \
        .props('boundary-links') \
        .classes('mt-6 justify-center')
    pagination.value = current_page['value']

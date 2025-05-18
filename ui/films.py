from nicegui import ui
from utils_api import load_videos
from functools import partial
from datetime import datetime

VIDEOS_PER_PAGE = 12

def navigate_to_film(video_id, e):
    ui.navigate.to(f'/film/{video_id}')

def films_page():
    current_page = {'value': 1}
    ui.label("🤼 Films, Films, and more Films!") \
        .classes('text-2xl font-bold mb-4 text-center')

    all_videos = load_videos()
    all_playlists = sorted(list({v['playlist_id'] for v in all_videos}))

    dates = [datetime.strptime(v['date'][:10], '%Y-%m-%d') for v in all_videos]
    min_date = min(dates).strftime('%Y-%m-%d') if dates else '1900-01-01'
    max_date = max(dates).strftime('%Y-%m-%d') if dates else '2100-01-01'

    default_date_range = f'{min_date} - {max_date}'

    with ui.splitter(horizontal=False, value=20).classes('w-full h-full rounded shadow') as splitter:
        with splitter.before:
            with ui.column().classes('w-full h-full p-6 bg-gray-100 rounded-lg space-y-4'):
                ui.label('🎛 Filters').classes('text-lg font-bold mb-4')

                playlist_filter = ui.select(
                    options=all_playlists,
                    value=all_playlists.copy(),
                    label='Playlist',
                    multiple=True,
                ).classes('w-full')

                # Collapsed date picker with selected date range display
                with ui.input('Date Range', value=f"{min_date} - {max_date}").classes('w-full') as date_input:
                    with ui.menu().props('no-parent-event') as menu:
                        with ui.date(value={'from': min_date, 'to': max_date}).props('range').bind_value(
                            date_input,
                            forward=lambda x: f"{x['from']} - {x['to']}" if x else None,
                            backward=lambda x: {
                                'from': x.split(' - ')[0],
                                'to': x.split(' - ')[1],
                            } if ' - ' in (x or '') else None,
                        ):
                            with ui.row().classes('justify-end'):
                                ui.button('Close', on_click=menu.close).props('flat')
                    with date_input.add_slot('append'):
                        ui.icon('edit_calendar').on('click', menu.open).classes('cursor-pointer')

                ui.button('Apply Filters', on_click=lambda: render_videos()).classes('mt-4 w-full')

        with splitter.after:
            with ui.column().classes('w-full h-full p-6 space-y-6'):
                video_grid = ui.column().classes('space-y-6')

                def render_videos():
                    # Parse the date range from the input value
                    date_range = date_input.value or f"{min_date} - {max_date}"
                    try:
                        start_date, end_date = date_range.split(" - ")
                    except ValueError:
                        # Fallback to default date range if parsing fails
                        start_date, end_date = min_date, max_date

                    # Filter videos based on the selected playlist and date range
                    filtered_videos = [
                        v for v in all_videos
                        if v['playlist_id'] in playlist_filter.value
                        and start_date <= v['date'][:10] <= end_date
                    ]

                    # Sort videos by date in descending order
                    videos_sorted = sorted(filtered_videos, key=lambda x: x['date'], reverse=True)

                    # Paginate videos
                    total_pages = max(1, (len(videos_sorted) + VIDEOS_PER_PAGE - 1) // VIDEOS_PER_PAGE)
                    start_index = (current_page['value'] - 1) * VIDEOS_PER_PAGE
                    end_index = start_index + VIDEOS_PER_PAGE
                    paginated_videos = videos_sorted[start_index:end_index]

                    # Group videos by date
                    grouped = {}
                    for v in paginated_videos:
                        day = v['date'][:10]
                        grouped.setdefault(day, []).append(v)

                    # Clear and populate the video grid
                    video_grid.clear()
                    for day, day_videos in grouped.items():
                        with video_grid:
                            ui.label(f'📅 {day}').classes('text-xl font-semibold text-blue-800')
                            with ui.grid().classes(
                                'grid auto-rows-max grid-cols-[repeat(auto-fit,minmax(250px,1fr))] gap-4 w-full'
                            ):
                                for v in day_videos:
                                    with ui.card().classes(
                                        'cursor-pointer hover:shadow-xl transition-shadow duration-200'
                                    ).on('click', partial(navigate_to_film, v["video_id"])):
                                        thumbnail_url = f'https://img.youtube.com/vi/{v["video_id"]}/0.jpg'
                                        ui.image(thumbnail_url).classes('w-full rounded aspect-video object-cover')
                                        ui.label(v["title"]).tooltip(v["title"]).classes('font-medium mt-2 truncate text-sm')
                            ui.separator().classes('my-4')
                    # Add pagination controls
                    with video_grid:
                        with ui.row().classes('justify-between items-center mt-4'):
                            ui.button('Previous', on_click=lambda: change_page(-1)).props('flat').classes('text-blue-500')
                            ui.label(f'Page {current_page["value"]} of {total_pages}').classes('text-sm font-medium')
                            ui.button('Next', on_click=lambda: change_page(1)).props('flat').classes('text-blue-500')

                def change_page(direction):
                    # Update the current page and re-render videos
                    total_pages = max(1, (len(all_videos) + VIDEOS_PER_PAGE - 1) // VIDEOS_PER_PAGE)
                    current_page['value'] = max(1, min(current_page['value'] + direction, total_pages))
                    render_videos()

                render_videos()

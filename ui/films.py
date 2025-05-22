from nicegui import ui
from utils_api import load_videos
from functools import partial
from datetime import datetime

VIDEOS_PER_PAGE = 12

def navigate_to_film(video_id, e):
    ui.navigate.to(f'/film/{video_id}')

def films_page():
    current_page = {'value': 1}
    ui.label("🎬 Films, Films, and more Films!") \
        .classes('text-2xl font-bold mb-4 text-center')

    all_videos = load_videos()
    all_playlists = sorted(list({v['playlist_name'] for v in all_videos}))

    # --- Collect all unique labels from all videos ---
    all_labels = sorted({label for v in all_videos for label in v.get('labels', [])})

    # --- Collect all unique partners from all videos ---
    all_partners = sorted({partner for v in all_videos for partner in v.get('partners', [])})

    dates = [datetime.strptime(v['date'][:10], '%Y-%m-%d') for v in all_videos]
    min_date = min(dates).strftime('%Y-%m-%d') if dates else '1900-01-01'
    max_date = max(dates).strftime('%Y-%m-%d') if dates else '2100-01-01'

    min_date_human = datetime.strptime(min_date, '%Y-%m-%d').strftime('%B %d, %Y')
    max_date_human = datetime.strptime(max_date, '%Y-%m-%d').strftime('%B %d, %Y')
    default_date_range = f'{min_date_human} - {max_date_human}'

    with ui.splitter(horizontal=False, value=20).classes('w-full h-full rounded shadow') as splitter:
        with splitter.before:
            with ui.column().classes('w-full h-full p-6 bg-gray-100 rounded-lg space-y-4'):
                ui.label('🎛 Filters').classes('text-lg font-bold mb-4')

                playlist_filter = ui.select(
                    options=all_playlists,
                    value=all_playlists.copy(),
                    label='Playlist',
                    multiple=True,
                ).classes('w-full').props('use-chips')

                # --- Label filter ---
                label_filter = ui.select(
                    options=all_labels,
                    value=[],
                    label='Labels',
                    multiple=True,
                ).classes('w-full').props('use-chips')

                # --- Partner filter ---
                partner_filter = ui.select(
                    options=all_partners,
                    value=[],
                    label='Partners',
                    multiple=True,
                ).classes('w-full').props('use-chips')

                # Collapsed date picker with selected date range display
                with ui.input('Date Range', value=default_date_range).classes('w-full') as date_input:
                    with ui.menu().props('no-parent-event') as menu:
                        with ui.date(value={'from': min_date, 'to': max_date}).props('range').bind_value(
                            date_input,
                            forward=lambda x: f"{datetime.strptime(x['from'], '%Y-%m-%d').strftime('%B %d, %Y')} - {datetime.strptime(x['to'], '%Y-%m-%d').strftime('%B %d, %Y')}" if x else None,
                            backward=lambda x: {
                                'from': datetime.strptime(x.split(' - ')[0], '%B %d, %Y').strftime('%Y-%m-%d'),
                                'to': datetime.strptime(x.split(' - ')[1], '%B %d, %Y').strftime('%Y-%m-%d'),
                            } if ' - ' in (x or '') else None,
                        ):
                            with ui.row().classes('justify-end'):
                                ui.button('Close', on_click=menu.close).props('flat')
                    with date_input.add_slot('append'):
                        ui.icon('edit_calendar').on('click', menu.open).classes('cursor-pointer')

                ui.button('Apply Filters', on_click=lambda: render_videos()).classes('mt-4 w-full')

        with splitter.after:
            # Enhanced grid container
            video_grid = ui.grid().classes(
                'grid auto-rows-max grid-cols-[repeat(auto-fit,minmax(250px,1fr))] gap-6 w-full p-4 bg-white rounded-lg shadow-lg'
            )

            def render_videos():
                # Parse the date range from the input value
                date_range = date_input.value or default_date_range
                try:
                    start_date, end_date = date_range.split(" - ")
                    start_date = datetime.strptime(start_date, '%B %d, %Y').strftime('%Y-%m-%d')
                    end_date = datetime.strptime(end_date, '%B %d, %Y').strftime('%Y-%m-%d')
                except ValueError:
                    # Fallback to default date range if parsing fails
                    start_date, end_date = min_date, max_date

                # --- Filter videos based on playlist, date, and labels ---
                filtered_videos = [
                    v for v in all_videos
                    if v['playlist_name'] in playlist_filter.value
                    and start_date <= v['date'][:10] <= end_date
                    and (not label_filter.value or any(label in v.get('labels', []) for label in label_filter.value))
                    and (not partner_filter.value or any(partner in v.get('partners', []) for partner in partner_filter.value))
                ]

                # Sort videos by date in descending order
                videos_sorted = sorted(filtered_videos, key=lambda x: x['date'], reverse=True)

                # Paginate videos
                total_pages = max(1, (len(videos_sorted) + VIDEOS_PER_PAGE - 1) // VIDEOS_PER_PAGE)
                start_index = (current_page['value'] - 1) * VIDEOS_PER_PAGE
                end_index = start_index + VIDEOS_PER_PAGE
                paginated_videos = videos_sorted[start_index:end_index]

                # Group paginated videos by date
                grouped_videos = {}
                for v in paginated_videos:
                    day = v['date'][:10]
                    if day not in grouped_videos:
                        grouped_videos[day] = []
                    grouped_videos[day].append(v)

                # Clear and populate the video grid
                video_grid.clear()
                with video_grid:
                    for day, day_videos in grouped_videos.items():
                        # Convert the date (day) to a human-readable format
                        human_readable_day = datetime.strptime(day, '%Y-%m-%d').strftime('%B %d, %Y')
                        
                        # Add a label for each date
                        ui.label(f"📅 {human_readable_day}").classes('text-xl font-semibold text-blue-500 col-span-full mb-4')
                        for v in day_videos:
                            # Enhanced video cards
                            with ui.card().classes(
                                'cursor-pointer hover:shadow-xl transition-shadow duration-200 border border-gray-300 rounded-lg'
                            ).on('click', partial(navigate_to_film, v["video_id"])):
                                thumbnail_url = f'https://img.youtube.com/vi/{v["video_id"]}/0.jpg'
                                ui.image(thumbnail_url).classes('w-full rounded aspect-video object-cover mb-2')
                                ui.label(v["title"]) \
                                    .tooltip(v["title"]) \
                                    .classes('font-medium mt-2 truncate text-sm sm:text-base text-gray-700')
                                # Display duration instead of date
                                ui.label(f"⏱ {v['duration_human']}") \
                                    .classes('text-sm text-gray-500')

                    # Enhanced pagination controls
                    with ui.row().classes('justify-between items-center mt-6 col-span-full'):
                        ui.button('Previous', on_click=lambda: change_page(-1)).props('flat').classes('text-blue-500 hover:text-blue-700')
                        ui.label(f'Page {current_page["value"]} of {total_pages}').classes('text-sm font-medium text-gray-700')
                        ui.button('Next', on_click=lambda: change_page(1)).props('flat').classes('text-blue-500 hover:text-blue-700')

            def change_page(direction):
                # Update the current page and re-render videos
                total_pages = max(1, (len(all_videos) + VIDEOS_PER_PAGE - 1) // VIDEOS_PER_PAGE)
                current_page['value'] = max(1, min(current_page['value'] + direction, total_pages))
                render_videos()

            render_videos()

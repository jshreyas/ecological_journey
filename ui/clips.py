from nicegui import ui
from utils_api import load_videos, load_clips, load_cliplist  # <-- New import for cliplist loading
from functools import partial
from datetime import datetime
from urllib.parse import urlparse

VIDEOS_PER_PAGE = 12

def navigate_to_film(video_id, clip_id):
    ui.navigate.to(f'/film/{video_id}?clip={clip_id}')

def clips_page(cliplist_id=None):
    current_page = {'value': 1}
    ui.label("🎬 Clips, Clips, and more Clips!") \
        .classes('text-2xl font-bold mb-4 text-center')

    all_videos = load_clips()
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

    cliplist_filter_override = None
    if cliplist_id:
        try:
            cliplist = load_cliplist(cliplist_id)
            cliplist_filter_override = {
                'clip_ids': set(cliplist['clip_ids']),
                'filters': cliplist.get('filters', {})
            }
        except Exception as e:
            ui.notify(f"⚠️ Failed to load cliplist: {e}", type="warning")

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

                # --- Label cloud filter ---
                ui.label("Labels").classes("font-semibold text-gray-600")
                label_chip_container = ui.row(wrap=True).classes("gap-2 max-h-40 overflow-auto")

                class ReactiveLabelSet:
                    def __init__(self):
                        self.labels = set()

                    def toggle(self, label: str):
                        if label in self.labels:
                            self.labels.remove(label)
                        else:
                            self.labels.add(label)
                        render_chips()  # Force re-render manually

                    def has(self, label: str):
                        return label in self.labels

                    def values(self):
                        return list(self.labels)

                selected_labels = ReactiveLabelSet()

                def render_chips():
                    label_chip_container.clear()
                    with label_chip_container:
                        for label in all_labels:
                            chip = ui.chip(label)
                            if selected_labels.has(label):
                                chip.props('color=primary outline')
                            else:
                                chip.props('color=grey-4 text-black')
                            chip.on_click(partial(selected_labels.toggle, label))
                render_chips()

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

                def apply_filters():
                    current_page['value'] = 1
                    render_videos()

                def save_filtered_clips():
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
                    filtered_clips = [
                        v for v in all_videos
                        if v['playlist_name'] in playlist_filter.value
                        and start_date <= v['date'][:10] <= end_date
                        and (not selected_labels.values() or any(label in v.get('labels', []) for label in selected_labels.values()))
                        and (not partner_filter.value or any(partner in v.get('partners', []) for partner in partner_filter.value))
                    ]

                    filters_state = {
                        "playlists": playlist_filter.value,
                        "labels": selected_labels.values(),
                        "partners": partner_filter.value,
                        "date_range": [start_date, end_date],
                    }
                    # Ask for cliplist name via dialog
                    with ui.dialog() as dialog, ui.card():
                        ui.label("Name your cliplist:")
                        name_input = ui.input(label='Cliplist Name')
                        def confirm_save():
                            # save_to_backend(name_input.value, filters_state, filtered_clips)
                            ui.notify(f"✅ Save successful with {name_input.value} and filters_state: {filters_state}", type="positive")
                            dialog.close()
                        ui.button("Save", on_click=confirm_save)
                    dialog.open()

                with ui.row().classes("justify-between w-full"):
                    ui.button('Apply', on_click=apply_filters).classes('mt-4')
                    ui.button('💾 Save', on_click=save_filtered_clips).classes('mt-4')

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
                    if (not cliplist_filter_override or v['clip_id'] in cliplist_filter_override['clip_ids'])
                    and v['playlist_name'] in playlist_filter.value
                    and start_date <= v['date'][:10] <= end_date
                    and (not selected_labels.values() or any(label in v.get('labels', []) for label in selected_labels.values()))
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
                    grouped_videos.setdefault(day, []).append(v)

                # Clear and populate the video grid
                video_grid.clear()
                with video_grid:
                    if not paginated_videos:
                        ui.label("No films found for the selected filters.").classes('text-center text-gray-400 col-span-full mb-8')
                    else:
                        for day, day_videos in grouped_videos.items():
                            # Convert the date (day) to a human-readable format
                            human_readable_day = datetime.strptime(day, '%Y-%m-%d').strftime('%B %d, %Y')
                            ui.label(f"📅 {human_readable_day}").classes('text-xl font-semibold text-blue-500 col-span-full mb-4')
                            for v in day_videos:
                                # Enhanced video cards
                                with ui.card().classes(
                                    'cursor-pointer hover:shadow-xl transition-shadow duration-200 border border-gray-300 rounded-lg'
                                ).on('click', partial(navigate_to_film, v["video_id"], v["clip_id"])):
                                    thumbnail_url = f'https://img.youtube.com/vi/{v["video_id"]}/0.jpg'
                                    ui.image(thumbnail_url).classes('w-full rounded aspect-video object-cover mb-2')
                                    ui.label(v["title"]).tooltip(v["title"]).classes('font-medium mt-2 truncate text-sm sm:text-base text-gray-700')
                                    ui.label(f"⏱ {v['duration_human']}").classes('text-sm text-gray-500')

                        # Enhanced pagination controls
                        with ui.row().classes('justify-between items-center mt-6 col-span-full'):
                            if current_page["value"] > 1:
                                ui.button('Previous', on_click=lambda: change_page(-1)).props('flat').classes('text-blue-500 hover:text-blue-700')
                            else:
                                ui.label()  # Empty placeholder for alignment

                            ui.label(f'Page {current_page["value"]} of {total_pages}').classes('text-sm font-medium text-gray-700')
                            if current_page["value"] < total_pages:
                                ui.button('Next', on_click=lambda: change_page(1)).props('flat').classes('text-blue-500 hover:text-blue-700')
                            else:
                                ui.label()  # Empty placeholder for alignment

            def change_page(direction):
                # Recalculate filtered_videos for correct total_pages
                date_range = date_input.value or default_date_range
                try:
                    start_date, end_date = date_range.split(" - ")
                    start_date = datetime.strptime(start_date, '%B %d, %Y').strftime('%Y-%m-%d')
                    end_date = datetime.strptime(end_date, '%B %d, %Y').strftime('%Y-%m-%d')
                except ValueError:
                    start_date, end_date = min_date, max_date

                filtered_videos = [
                    v for v in all_videos
                    if (not cliplist_filter_override or v['clip_id'] in cliplist_filter_override['clip_ids'])
                    and v['playlist_name'] in playlist_filter.value
                    and start_date <= v['date'][:10] <= end_date
                    and (not selected_labels.values() or any(label in v.get('labels', []) for label in selected_labels.values()))
                    and (not partner_filter.value or any(partner in v.get('partners', []) for partner in partner_filter.value))
                ]

                total_pages = max(1, (len(filtered_videos) + VIDEOS_PER_PAGE - 1) // VIDEOS_PER_PAGE)
                current_page['value'] = max(1, min(current_page['value'] + direction, total_pages))
                render_videos()

            render_videos()

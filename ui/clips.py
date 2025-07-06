from nicegui import ui, app
from dialog_puns import in_progress
from utils_api import load_clips, load_cliplist, save_cliplist
from functools import partial
from datetime import datetime

VIDEOS_PER_PAGE = 12

def navigate_to_cliplist(cliplist_id):
    ui.navigate.to(f'/cliplist/{cliplist_id}')

def navigate_to_film(video_id, clip_id):
    ui.navigate.to(f'/film/{video_id}?clip={clip_id}')

def clips_page():
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
    with ui.splitter(horizontal=False, value=20).classes('w-full h-full rounded shadow') as splitter:
        with splitter.before:
            with ui.tabs().classes('w-full mb-2') as tabs:
                tab_filter = ui.tab('🎛 Filters')
                tab_cliplists = ui.tab('📂 Cliplists')
            with ui.tab_panels(tabs=tabs, value=tab_filter).classes('w-full'):
                with ui.tab_panel(tab_filter):
                    with ui.column().classes('w-full h-full p-4 bg-gray-100 rounded-lg space-y-4'):
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
                                render_chips()
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
                            date_range = date_input.value or default_date_range
                            try:
                                start_date, end_date = date_range.split(" - ")
                                start_date = datetime.strptime(start_date, '%B %d, %Y').strftime('%Y-%m-%d')
                                end_date = datetime.strptime(end_date, '%B %d, %Y').strftime('%Y-%m-%d')
                            except ValueError:
                                start_date, end_date = min_date, max_date

                            # --- Filter videos based on playlist, date, and labels ---
                            filtered_clips = [
                                v for v in all_videos
                                if v['playlist_name'] in playlist_filter.value
                                and start_date <= v['date'][:10] <= end_date
                                and (not selected_labels.values() or any(label in v.get('labels', []) for label in selected_labels.values()))
                                and (not partner_filter.value or any(partner in v.get('partners', []) for partner in partner_filter.value))
                            ]
                            filtered_clip_ids = [v['video_id'] for v in filtered_clips]
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
                                daterange_checkbox = ui.checkbox('Lock Date Range')
                                def confirm_save(): #TODO: if not logged in, john doe response
                                    if not daterange_checkbox.value:
                                        filters_state['date_range'] = []
                                    save_cliplist(name_input.value, filters_state, token=app.storage.user.get("token"))
                                    #TODO: check failure and notify user of the failure
                                    ui.notify(f"✅ Save successful with {name_input.value} and filters_state: {filters_state}", type="positive")
                                    dialog.close()
                                    # Refresh the cliplists tab
                                ui.button("Save", on_click=confirm_save)
                            dialog.open()

                        with ui.row().classes("justify-between w-full"):
                            ui.button('Apply', on_click=apply_filters).classes('mt-4')
                            ui.button('💾 Save', on_click=save_filtered_clips).classes('mt-4')

                with ui.tab_panel(tab_cliplists).classes('w-full'):
                    saved_cliplists = load_cliplist()

                    cliplist_cards = ui.column().classes("overflow-y-auto h-full w-full gap-4")

                    def on_select_cliplist(cliplist):
                        cliplist_filter_override = {
                            'clip_ids': set(cliplist['clip_ids']),
                            'filters': cliplist.get('filters', {})
                        }
                        render_videos(cliplist_filter_override)

                    for cliplist in saved_cliplists:
                        with cliplist_cards:
                            with ui.card().classes('p-4 shadow-md bg-white rounded-lg border w-full'):
                                ui.label(cliplist['name']).classes('font-bold text-lg')
                                ui.label(f"🏷️ #labels: {', '.join(cliplist['filters'].get('labels', []))}").classes('text-sm text-gray-600')
                                ui.label(f"🧑‍🤝‍🧑 @partners: {', '.join(cliplist['filters'].get('partners', []))}").classes('text-sm text-gray-600')
                                ui.label(f"📂 playlists: {', '.join(cliplist['filters'].get('playlists', []))}").classes('text-sm text-gray-600 italic mb-2')
                                with ui.row().classes("gap-2"):
                                    ui.button(icon='filter_alt', on_click=lambda c=cliplist: on_select_cliplist(c)).props('flat').tooltip('Filter')
                                    ui.button(icon='play_arrow', on_click=lambda c=cliplist: navigate_to_cliplist(c["_id"])).props('flat color=secondary').tooltip('Play')
                                    ui.button(icon='delete', on_click=lambda c=cliplist: in_progress()).props('flat color=red').tooltip('Trash')

        with splitter.after:
            # Enhanced grid container
            video_grid = ui.grid().classes(
                'grid auto-rows-max grid-cols-[repeat(auto-fit,minmax(250px,1fr))] gap-6 w-full p-4 bg-white rounded-lg shadow-lg'
            )

            def render_videos(cliplist_filter_override=None):
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
                # Determine filters to apply
                filters_to_use = {
                    "playlists": playlist_filter.value,
                    "labels": selected_labels.values(),
                    "partners": partner_filter.value,
                    "date_range": [start_date, end_date],
                }
                if cliplist_filter_override and 'filters' in cliplist_filter_override:
                    filters_to_use.update({
                        "playlists": cliplist_filter_override['filters'].get('playlists', all_playlists),
                        "labels": cliplist_filter_override['filters'].get('labels', []),
                        "partners": cliplist_filter_override['filters'].get('partners', []),
                        "date_range": cliplist_filter_override['filters'].get('date_range', [min_date, max_date]),
                    })

                # Apply date range override
                date_range_override = filters_to_use["date_range"]
                if date_range_override and len(date_range_override) == 2:
                    start_date, end_date = date_range_override
                else:
                    start_date, end_date = min_date, max_date

                # Apply all filters
                filtered_videos = [
                    v for v in all_videos
                    if v['playlist_name'] in filters_to_use['playlists']
                    and start_date <= v['date'][:10] <= end_date
                    and (not filters_to_use['labels'] or any(label in v.get('labels', []) for label in filters_to_use['labels']))
                    and (not filters_to_use['partners'] or any(partner in v.get('partners', []) for partner in filters_to_use['partners']))
                ]

                # --- Group ALL filtered videos by date for correct counts ---
                all_grouped_counts = {}
                for v in filtered_videos:
                    day = v['date'][:10]
                    all_grouped_counts[day] = all_grouped_counts.get(day, 0) + 1

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
                            human_readable_day = datetime.strptime(day, '%Y-%m-%d').strftime('%B %d, %Y')
                            total_for_day = all_grouped_counts.get(day, len(day_videos))
                            ui.label(f"📅 {human_readable_day} ({total_for_day})").classes('text-xl font-semibold text-blue-500 col-span-full mb-4')
                            for v in day_videos:
                                partners = v.get("partners", [])
                                labels = v.get("labels", [])
                                partners_html = ", ".join(p for p in partners) if partners else "No partners"
                                labels_html = ", ".join(l for l in labels) if labels else "No labels"

                                with ui.card().classes(
                                    'cursor-pointer flex flex-row flex-col p-2 hover:shadow-xl transition-shadow duration-200 border-gray-600'
                                ).on('click', partial(navigate_to_film, v["video_id"], v["clip_id"])):
                                    with ui.row().classes('w-full gap-2 justify-between'):
                                        ui.label(v["title"]).tooltip(v["title"]).classes('truncate font-bold text-sm sm:text-base')
                                        ui.label(f"⏱ {v['duration_human']}").classes('text-xs')
                                    ui.label(f"🎭 {partners_html}").classes('text-xs')
                                    ui.label(f"🏷️ {labels_html}").classes('text-xs')
                                    ui.label(f"📂 {v['playlist_name']}").classes('text-xs text-blue-500')

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

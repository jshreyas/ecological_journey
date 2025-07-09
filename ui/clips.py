from nicegui import ui, app
from dialog_puns import in_progress
from utils_api import load_clips, load_cliplist, save_cliplist
from functools import partial
from datetime import datetime
import re

VIDEOS_PER_PAGE = 30

# --- Utility for parsing and checking query syntax ---
def parse_query_expression(tokens):
    # Precedence: NOT > AND > OR

    def parse(tokens):
        def parse_not(index):
            if tokens[index] == 'NOT':
                sub_expr, next_index = parse_not(index + 1)
                return ('NOT', sub_expr), next_index
            else:
                return tokens[index], index + 1

        def parse_and(index):
            left, index = parse_not(index)
            while index < len(tokens) and tokens[index] == 'AND':
                right, index = parse_not(index + 1)
                left = ('AND', left, right)
            return left, index

        def parse_or(index):
            left, index = parse_and(index)
            while index < len(tokens) and tokens[index] == 'OR':
                right, index = parse_and(index + 1)
                left = ('OR', left, right)
            return left, index

        ast, _ = parse_or(0)
        return ast

    def evaluate_ast(ast, clip_labels):
        if isinstance(ast, str):
            return ast in clip_labels
        if isinstance(ast, tuple):
            op = ast[0]
            if op == 'NOT':
                return not evaluate_ast(ast[1], clip_labels)
            elif op == 'AND':
                return evaluate_ast(ast[1], clip_labels) and evaluate_ast(ast[2], clip_labels)
            elif op == 'OR':
                return evaluate_ast(ast[1], clip_labels) or evaluate_ast(ast[2], clip_labels)
        return True  # Fallback

    ast = parse(tokens)

    def evaluate(clip_labels):
        return evaluate_ast(ast, clip_labels)

    return evaluate


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
            with ui.tabs().classes('w-full h-full') as tabs:
                tab_filter = ui.tab('🎛 Filters')
            with ui.tab_panels(tabs=tabs, value=tab_filter).classes('w-full h-full'):
                with ui.tab_panel(tab_filter):
                    with ui.column().classes('w-full h-full p-4 bg-gray-100 rounded-lg space-y-2'):
                        playlist_filter = ui.select(
                            options=all_playlists,
                            value=all_playlists.copy(),
                            label='Playlist',
                            multiple=True,
                        ).classes('w-full').props('use-chips')

                        # --- Label Query Builder ---
                        query_tokens = []
                        query_display_row = ui.row(wrap=True).classes("gap-2 p-1 bg-white border border-gray-300 w-full rounded min-h-[2rem]").tooltip(
                            "ex: 'label1 AND label2 OR NOT label3'"
                        )

                        def refresh_query_bar():
                            query_display_row.clear()
                            with query_display_row:
                                for token in query_tokens:
                                    ui.chip(token).classes('text-xs bg-blue-100 text-blue-800').props('outline').on_click(lambda t=token: query_tokens.remove(t) or refresh_query_bar())
                            try:
                                _ = parse_query_expression(query_tokens)
                                ui.notify("✅ Valid syntax")
                            except Exception:
                                ui.notify("⚠️ Invalid label query", color='negative')

                        def add_operator(op):
                            if not query_tokens:
                                if op == 'NOT':
                                    query_tokens.append(op)
                            else:
                                last = query_tokens[-1]
                                if op == 'NOT':
                                    # Allow NOT after AND/OR/label, but not after NOT
                                    if last not in ('NOT',):
                                        query_tokens.append(op)
                                elif last not in ('AND', 'OR', 'NOT'):
                                    query_tokens.append(op)
                            refresh_query_bar()

                        def on_label_click(label):
                            if query_tokens:
                                last = query_tokens[-1]
                                if last not in ('AND', 'OR', 'NOT'):
                                    # If last is a label, force operator OR between labels)
                                    query_tokens.append("OR")
                            query_tokens.append(label)
                            refresh_query_bar()

                        label_chip_container = ui.row(wrap=True).classes(
                            "gap-2 max-h-40 overflow-auto w-full border border-gray-300 rounded pt-0 pr-2 pb-2 pl-2 bg-white relative"
                        )

                        with label_chip_container:
                            # Sticky operator chips
                            with ui.row().classes("gap-2 sticky top-0 w-full bg-white z-10"):
                                for op in ['AND', 'OR', 'NOT']:
                                    ui.chip(op).on_click(partial(add_operator, op)).classes('text-xs bg-grey-4 text-primary')

                            # Scrollable label chips
                            for label in all_labels:
                                chip = ui.chip(label).on_click(partial(on_label_click, label))
                                chip.props('color=grey-3 text-black text-xs')

                        ui.separator().classes('border-gray-300 w-full')
                        # --- Partner Query Builder ---
                        pquery_tokens = []
                        pquery_display_row = ui.row(wrap=True).classes("gap-2 p-1 bg-white border border-gray-300 w-full rounded min-h-[2rem]").tooltip(
                            "ex: 'partner1 AND partner2 OR NOT partner3'"
                        )

                        def refresh_pquery_bar():
                            pquery_display_row.clear()
                            with pquery_display_row:
                                for token in pquery_tokens:
                                    ui.chip(token).classes('text-xs bg-blue-100 text-blue-800').props('outline').on_click(lambda t=token: pquery_tokens.remove(t) or refresh_pquery_bar())
                            try:
                                _ = parse_query_expression(pquery_tokens)
                                ui.notify("✅ Valid syntax")
                            except Exception as exc:
                                ui.notify(f"⚠️ Invalid partner query: {exc}", color='negative')

                        def padd_operator(op):
                            if not pquery_tokens:
                                if op == 'NOT':
                                    pquery_tokens.append(op)
                            else:
                                last = pquery_tokens[-1]
                                if op == 'NOT':
                                    # Allow NOT after AND/OR/label, but not after NOT
                                    if last not in ('NOT',):
                                        pquery_tokens.append(op)
                                elif last not in ('AND', 'OR', 'NOT'):
                                    pquery_tokens.append(op)
                            refresh_pquery_bar()

                        def on_partner_click(label):
                            if pquery_tokens:
                                last = pquery_tokens[-1]
                                if last not in ('AND', 'OR', 'NOT'):
                                    # If last is a partner, force operator OR between partners)
                                    pquery_tokens.append("OR")
                            pquery_tokens.append(label)
                            refresh_pquery_bar()

                        partner_chip_container = ui.row(wrap=True).classes(
                            "gap-2 max-h-40 overflow-auto w-full border border-gray-300 rounded pt-0 pr-2 pb-2 pl-2 bg-white relative"
                        )

                        with partner_chip_container:
                            # Sticky operator chips
                            with ui.row().classes("gap-2 sticky top-0 w-full bg-white z-10"):
                                for op in ['AND', 'OR', 'NOT']:
                                    ui.chip(op).on_click(partial(padd_operator, op)).classes('text-xs bg-grey-4 text-primary')

                            # Scrollable partner chips
                            for partner in all_partners:
                                chip = ui.chip(partner).on_click(partial(on_partner_click, partner))
                                chip.props('color=grey-3 text-black text-xs')

                        ui.separator().classes('border-gray-300 w-full')
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

                        #TODO: update this to save label queries instead of just labels
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

        with splitter.after:
            video_grid = ui.grid().classes(
                'grid auto-rows-max grid-cols-[repeat(auto-fit,minmax(250px,1fr))] gap-4 w-full p-4 bg-white rounded-lg shadow-lg'
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

                parsed_fn = parse_query_expression(query_tokens) if query_tokens else lambda labels: True
                pparsed_fn = parse_query_expression(pquery_tokens) if pquery_tokens else lambda partners: True

                filtered_videos = [
                    v for v in all_videos
                    if v['playlist_name'] in playlist_filter.value
                    and start_date <= v['date'][:10] <= end_date
                    and parsed_fn(v.get('labels', []))
                    and pparsed_fn(v.get('partners', []))
                ]
                ui.notify("🔍 Filtered videos: " + str(len(filtered_videos)), color='info')
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
                            ui.label(f"📅 {human_readable_day} ({total_for_day})").classes('text-xl font-semibold text-primary col-span-full mb-2')
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
                                    ui.label(f"📂 {v['playlist_name']}").classes('text-xs text-primary')
                            ui.separator().classes('border-gray-300 col-span-full')

                        # Enhanced pagination controls
                        with ui.row().classes('justify-between items-center col-span-full'):
                            if current_page["value"] > 1:
                                ui.button('Previous', on_click=lambda: change_page(-1)).props('flat').classes('text-primary hover:text-blue-700')
                            else:
                                ui.label()  # Empty placeholder for alignment

                            ui.label(f'Page {current_page["value"]} of {total_pages}').classes('text-sm font-medium text-gray-700')
                            if current_page["value"] < total_pages:
                                ui.button('Next', on_click=lambda: change_page(1)).props('flat').classes('text-primary hover:text-blue-700')
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
                parsed_fn = parse_query_expression(query_tokens) if query_tokens else lambda labels: True
                pparsed_fn = parse_query_expression(pquery_tokens) if pquery_tokens else lambda partners: True

                filtered_videos = [
                    v for v in all_videos
                    if v['playlist_name'] in playlist_filter.value
                    and start_date <= v['date'][:10] <= end_date
                    and parsed_fn(v.get('labels', []))
                    and pparsed_fn(v.get('partners', []))
                ]

                total_pages = max(1, (len(filtered_videos) + VIDEOS_PER_PAGE - 1) // VIDEOS_PER_PAGE)
                current_page['value'] = max(1, min(current_page['value'] + direction, total_pages))
                render_videos()

            render_videos()

import re
from datetime import datetime
from functools import partial

from nicegui import ui
from utils.dialog_puns import caught_john_doe
from utils.utils import navigate_to_film, parse_query_expression


class QueryBuilder:
    def __init__(self, items, title, tooltip):
        self.tokens = []
        self.items = items
        self.title = title
        self.tooltip = tooltip
        self.display_row = (
            ui.row(wrap=True)
            .classes("gap-2 p-1 bg-white border border-gray-300 w-full rounded min-h-[2rem]")
            .tooltip(self.tooltip)
        )
        self._build_ui()

    def _build_ui(self):
        ui.label(self.title).classes("font-semibold text-gray-600")
        self._render_operators()
        self._render_items()

    def _render_operators(self):
        with ui.row().classes("gap-2 sticky top-0 w-full bg-white z-10"):
            for op in ["AND", "OR", "NOT"]:
                ui.chip(op).on_click(partial(self.add_operator, op)).classes("text-xs bg-grey-4 text-primary")

    def _render_items(self):
        container = ui.row(wrap=True).classes(
            "gap-2 max-h-40 overflow-auto w-full border border-gray-300 rounded pt-0 pr-2 pb-2 pl-2 bg-white relative"
        )
        with container:
            for item in self.items:
                chip = ui.chip(item).on_click(partial(self.add_item, item))
                chip.props("color=grey-3 text-black text-xs")

    def refresh(self):
        self.display_row.clear()
        with self.display_row:
            for token in self.tokens:
                ui.chip(token).classes("text-xs bg-blue-100 text-blue-800").props("outline").on_click(
                    lambda t=token: self.tokens.remove(t) or self.refresh()
                )
        try:
            _ = parse_query_expression(self.tokens)
            ui.notify("✅ Valid syntax")
        except Exception as exc:
            ui.notify(f"⚠️ Invalid query: {exc}", color="negative")

    def add_operator(self, op):
        if not self.tokens:
            if op == "NOT":
                self.tokens.append(op)
        else:
            last = self.tokens[-1]
            if op == "NOT":
                if last not in ("NOT",):
                    self.tokens.append(op)
            elif last not in ("AND", "OR", "NOT"):
                self.tokens.append(op)
        self.refresh()

    def add_item(self, item):
        if self.tokens:
            last = self.tokens[-1]
            if last not in ("AND", "OR", "NOT"):
                self.tokens.append("OR")
        self.tokens.append(item)
        self.refresh()


def render_query_builders(all_labels, all_partners):
    label_qb = QueryBuilder(
        items=all_labels,
        title="Labels",
        tooltip="ex: 'label1 AND label2 OR NOT label3'",
    )
    partner_qb = QueryBuilder(
        items=all_partners,
        title="Partners",
        tooltip="ex: 'partner1 AND partner2 OR NOT partner3'",
    )
    return label_qb, partner_qb


def render_media_page(
    *,
    title,
    data_loader,
    save_cliplist=None,
    user=None,
    show_save_button=False,
    show_clips_count=False,
):
    current_page = {"value": 1}
    label = (m := re.search(r"🎬 (\w+),", title)) and m.group(1)
    ui.label(title).classes("text-2xl font-bold mb-4 text-center")

    all_videos = data_loader()
    all_playlists = sorted(list({v["playlist_name"] for v in all_videos}))
    all_labels = sorted({label for v in all_videos for label in v.get("labels", [])})
    all_partners = sorted({partner for v in all_videos for partner in v.get("partners", [])})

    dates = [datetime.strptime(v["date"][:10], "%Y-%m-%d") for v in all_videos]
    min_date = min(dates).strftime("%Y-%m-%d") if dates else "1900-01-01"
    max_date = max(dates).strftime("%Y-%m-%d") if dates else "2100-01-01"
    min_date_human = datetime.strptime(min_date, "%Y-%m-%d").strftime("%B %d, %Y")
    max_date_human = datetime.strptime(max_date, "%Y-%m-%d").strftime("%B %d, %Y")
    default_date_range = f"{min_date_human} - {max_date_human}"

    with ui.splitter(horizontal=False, value=20).classes("w-full h-full rounded shadow") as splitter:
        with splitter.before:
            with ui.column().classes("w-full h-full p-4 bg-gray-100 rounded-lg"):
                playlist_filter = (
                    ui.select(
                        options=all_playlists,
                        value=all_playlists.copy(),
                        label="Playlist",
                        multiple=True,
                    )
                    .classes("w-full")
                    .props("use-chips")
                )

                label_qb, partner_qb = render_query_builders(all_labels, all_partners)

                ui.separator().classes("border-gray-300 w-full")

                with ui.input("Date Range", value=default_date_range).classes("w-full") as date_input:
                    with ui.menu().props("no-parent-event") as menu:
                        with (
                            ui.date(value={"from": min_date, "to": max_date})
                            .props("range")
                            .bind_value(
                                date_input,
                                forward=lambda x: (
                                    f"{datetime.strptime(x['from'], '%Y-%m-%d').strftime('%B %d, %Y')} - {datetime.strptime(x['to'], '%Y-%m-%d').strftime('%B %d, %Y')}"
                                    if x
                                    else None
                                ),
                                backward=lambda x: (
                                    {
                                        "from": datetime.strptime(x.split(" - ")[0], "%B %d, %Y").strftime("%Y-%m-%d"),
                                        "to": datetime.strptime(x.split(" - ")[1], "%B %d, %Y").strftime("%Y-%m-%d"),
                                    }
                                    if " - " in (x or "")
                                    else None
                                ),
                            )
                        ):
                            with ui.row().classes("justify-end"):
                                ui.button("Close", on_click=menu.close).props("flat")
                    with date_input.add_slot("append"):
                        ui.icon("edit_calendar").on("click", menu.open).classes("cursor-pointer")

                def apply_filters():
                    current_page["value"] = 1
                    render_videos()

                def save_filtered_clips():
                    if not save_cliplist:
                        return
                    date_range = date_input.value or default_date_range
                    try:
                        start_date, end_date = date_range.split(" - ")
                        start_date = datetime.strptime(start_date, "%B %d, %Y").strftime("%Y-%m-%d")
                        end_date = datetime.strptime(end_date, "%B %d, %Y").strftime("%Y-%m-%d")
                    except ValueError:
                        start_date, end_date = min_date, max_date

                    filters_state = {
                        "playlists": playlist_filter.value,
                        "labels": label_qb.tokens,
                        "partners": partner_qb.tokens,
                        "date_range": [start_date, end_date],
                    }
                    with ui.dialog() as dialog, ui.card():
                        ui.label("Name your cliplist:")
                        name_input = ui.input(label="Cliplist Name")
                        daterange_checkbox = ui.checkbox("Lock Date Range")

                        def confirm_save():
                            if not user:
                                caught_john_doe()
                                return
                            if not daterange_checkbox.value:
                                filters_state["date_range"] = []

                            result = save_cliplist(
                                name_input.value,
                                filters_state,
                                token=user.token,
                            )
                            if result:
                                ui.notify(
                                    f"✅ Save successful with {name_input.value} and filters_state: {filters_state}",
                                    type="positive",
                                )
                            else:
                                ui.notify("Cliplist creation failed", type="negative")
                            dialog.close()

                        ui.button(icon="save", on_click=confirm_save)
                    dialog.open()

                with ui.row().classes("justify-between w-full"):
                    ui.button(icon="filter_alt", on_click=apply_filters).classes("mt-4")
                    if show_save_button:
                        ui.button(icon="save", on_click=save_filtered_clips).classes("mt-4")

        with splitter.after:
            video_grid = ui.grid().classes(
                "grid auto-rows-max grid-cols-[repeat(auto-fit,minmax(250px,1fr))] gap-4 w-full p-4 bg-white rounded-lg shadow-lg"
            )

            def render_videos():
                date_range = date_input.value or default_date_range
                try:
                    start_date, end_date = date_range.split(" - ")
                    start_date = datetime.strptime(start_date, "%B %d, %Y").strftime("%Y-%m-%d")
                    end_date = datetime.strptime(end_date, "%B %d, %Y").strftime("%Y-%m-%d")
                except ValueError:
                    start_date, end_date = min_date, max_date

                parse_label_fn = parse_query_expression(label_qb.tokens) if label_qb.tokens else lambda labels: True
                parse_partner_fn = (
                    parse_query_expression(partner_qb.tokens) if partner_qb.tokens else lambda partners: True
                )

                filtered_videos = [
                    v
                    for v in all_videos
                    if v["playlist_name"] in playlist_filter.value
                    and start_date <= v["date"][:10] <= end_date
                    and parse_label_fn(v.get("labels", []))
                    and parse_partner_fn(v.get("partners", []))
                ]

                ui.notify(f"🔍 Filtered {label}: {len(filtered_videos)}", color="green")
                all_grouped_counts = {}
                for v in filtered_videos:
                    day = v["date"][:10]
                    all_grouped_counts[day] = all_grouped_counts.get(day, 0) + 1

                videos_sorted = sorted(filtered_videos, key=lambda x: x["date"], reverse=True)
                VIDEOS_PER_PAGE = 30
                total_pages = max(1, (len(videos_sorted) + VIDEOS_PER_PAGE - 1) // VIDEOS_PER_PAGE)
                start_index = (current_page["value"] - 1) * VIDEOS_PER_PAGE
                end_index = start_index + VIDEOS_PER_PAGE
                paginated_videos = videos_sorted[start_index:end_index]

                grouped_videos = {}
                for v in paginated_videos:
                    day = v["date"][:10]
                    grouped_videos.setdefault(day, []).append(v)

                video_grid.clear()
                with video_grid:
                    if not paginated_videos:
                        ui.label(f"No {label} found for the selected filters.").classes(
                            "text-center text-gray-400 col-span-full mb-8"
                        )
                    else:
                        for day, day_videos in grouped_videos.items():
                            human_readable_day = datetime.strptime(day, "%Y-%m-%d").strftime("%B %d, %Y")
                            total_for_day = all_grouped_counts.get(day, len(day_videos))
                            ui.label(f"🗓️ {human_readable_day} ({total_for_day})").classes(
                                "text-xl font-semibold text-primary col-span-full mb-2"
                            )
                            for v in day_videos:
                                partners = v.get("partners", [])
                                labels = v.get("labels", [])
                                partners_html = ", ".join(p for p in partners) if partners else "No partners"
                                labels_html = ", ".join(label for label in labels) if labels else "No labels"
                                with (
                                    ui.card()
                                    .classes(
                                        "cursor-pointer flex flex-row flex-col p-2 hover:shadow-xl transition-shadow duration-200 border-gray-600"
                                    )
                                    .on(
                                        "click",
                                        partial(navigate_to_film, v["video_id"], v.get("clip_id")),
                                    )
                                ):
                                    with ui.row().classes("w-full gap-2 justify-between"):
                                        ui.label(v["title"]).tooltip(v["title"]).classes(
                                            "truncate font-bold text-sm sm:text-base"
                                        )
                                        ui.label(f"⏱ {v['duration_human']}").classes("text-xs")
                                    ui.label(f"🎭 {partners_html}").classes("text-xs")
                                    ui.label(f"🏷️ {labels_html}").classes("text-xs")
                                    ui.label(f"📂 {v['playlist_name']}").classes("text-xs text-primary")
                                    if show_clips_count:
                                        ui.label(f"🎬 {len(v.get('clips', []))}").classes("text-xs")
                            ui.separator().classes("border-gray-300 col-span-full")

                        with ui.row().classes("justify-between items-center col-span-full"):
                            if current_page["value"] > 1:
                                ui.button("Previous", on_click=lambda: change_page(-1)).props("flat").classes(
                                    "text-primary hover:text-blue-700"
                                )
                            else:
                                ui.label()
                            ui.label(f'Page {current_page["value"]} of {total_pages}').classes(
                                "text-sm font-medium text-gray-700"
                            )
                            if current_page["value"] < total_pages:
                                ui.button("Next", on_click=lambda: change_page(1)).props("flat").classes(
                                    "text-primary hover:text-blue-700"
                                )
                            else:
                                ui.label()

            def change_page(direction):
                date_range = date_input.value or default_date_range
                try:
                    start_date, end_date = date_range.split(" - ")
                    start_date = datetime.strptime(start_date, "%B %d, %Y").strftime("%Y-%m-%d")
                    end_date = datetime.strptime(end_date, "%B %d, %Y").strftime("%Y-%m-%d")
                except ValueError:
                    start_date, end_date = min_date, max_date

                parse_label_fn = parse_query_expression(label_qb.tokens) if label_qb.tokens else lambda labels: True
                parse_partner_fn = (
                    parse_query_expression(partner_qb.tokens) if partner_qb.tokens else lambda partners: True
                )
                filtered_videos = [
                    v
                    for v in all_videos
                    if v["playlist_name"] in playlist_filter.value
                    and start_date <= v["date"][:10] <= end_date
                    and parse_label_fn(v.get("labels", []))
                    and parse_partner_fn(v.get("partners", []))
                ]
                VIDEOS_PER_PAGE = 30
                total_pages = max(1, (len(filtered_videos) + VIDEOS_PER_PAGE - 1) // VIDEOS_PER_PAGE)
                current_page["value"] = max(1, min(current_page["value"] + direction, total_pages))
                render_videos()

            render_videos()

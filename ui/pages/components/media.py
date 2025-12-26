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

        ui.label(self.title).classes("font-semibold text-gray-600")

        self.display_row = (
            ui.row(wrap=True)
            .classes("gap-2 p-1 bg-white border border-gray-300 w-full rounded min-h-[2rem]")
            .tooltip(self.tooltip)
        )

        self._build_ui()

    def _build_ui(self):
        self._render_operators()
        self._render_items()

    def _render_operators(self):
        with ui.row().classes("gap-2 sticky top-0 w-full bg-white z-10"):
            for op in ["AND", "OR", "NOT"]:
                ui.chip(op).classes("text-xs bg-grey-4 text-primary").on_click(partial(self.add_operator, op))

    def _render_items(self):
        with ui.row(wrap=True).classes(
            "gap-2 max-h-40 overflow-auto w-full border border-gray-300 rounded p-2 bg-white"
        ):
            for item in self.items:
                ui.chip(item).props("color=grey-3 text-black text-xs").on_click(partial(self.add_item, item))

    def refresh(self):
        self.display_row.clear()
        with self.display_row:
            for token in self.tokens:
                ui.chip(token).classes("text-xs bg-blue-100 text-blue-800").props("outline").on_click(
                    lambda t=token: self.tokens.remove(t) or self.refresh()
                )

        try:
            parse_query_expression(self.tokens)
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
                if last != "NOT":
                    self.tokens.append(op)
            elif last not in ("AND", "OR", "NOT"):
                self.tokens.append(op)
        self.refresh()

    def add_item(self, item):
        if self.tokens and self.tokens[-1] not in ("AND", "OR", "NOT"):
            self.tokens.append("OR")
        self.tokens.append(item)
        self.refresh()


class MediaFilterState:
    def __init__(self, all_playlists, min_date, max_date):
        self.all_playlists = all_playlists
        self.selected_playlists = []

        self.label_tokens = []
        self.partner_tokens = []

        self.start_date = min_date
        self.end_date = max_date

        self.page = 1
        self.VIDEOS_PER_PAGE = 30

    def apply(self, all_videos):
        label_fn = parse_query_expression(self.label_tokens) if self.label_tokens else lambda _: True
        partner_fn = parse_query_expression(self.partner_tokens) if self.partner_tokens else lambda _: True

        playlists = self.selected_playlists or self.all_playlists

        return [
            v
            for v in all_videos
            if v["playlist_name"] in playlists
            and self.start_date <= v["date"][:10] <= self.end_date
            and label_fn(v.get("labels", []))
            and partner_fn(v.get("partners", []))
        ]

    def to_cliplist_payload(self):
        return {
            "playlists": self.selected_playlists or self.all_playlists,
            "labels": self.label_tokens,
            "partners": self.partner_tokens,
            "date_range": [self.start_date, self.end_date],
        }


def render_query_builders(all_labels, all_partners):
    label_qb = QueryBuilder(
        items=all_labels,
        title="Labels",
        tooltip="ex: label1 AND label2 OR NOT label3",
    )

    ui.separator().classes("border-gray-300 w-full")

    partner_qb = QueryBuilder(
        items=all_partners,
        title="Partners",
        tooltip="ex: partner1 AND partner2 OR NOT partner3",
    )

    return label_qb, partner_qb


def render_date_picker(min_date, max_date, state: MediaFilterState):
    min_h = datetime.strptime(min_date, "%Y-%m-%d").strftime("%B %d, %Y")
    max_h = datetime.strptime(max_date, "%Y-%m-%d").strftime("%B %d, %Y")
    default_range = f"{min_h} - {max_h}"

    with ui.input("Date Range", value=default_range).classes("w-full") as date_input:
        with ui.menu().props("no-parent-event") as menu:

            ui.date(value={"from": min_date, "to": max_date}).props("range").bind_value(
                date_input,
                forward=lambda x: (
                    f"{datetime.strptime(x['from'], '%Y-%m-%d').strftime('%B %d, %Y')} - "
                    f"{datetime.strptime(x['to'], '%Y-%m-%d').strftime('%B %d, %Y')}"
                    if x and x.get("from") and x.get("to")
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

        with date_input.add_slot("append"):
            ui.icon("edit_calendar").classes("cursor-pointer").on("click", menu.open)

    def update_state():
        try:
            start, end = date_input.value.split(" - ")
            state.start_date = datetime.strptime(start, "%B %d, %Y").strftime("%Y-%m-%d")
            state.end_date = datetime.strptime(end, "%B %d, %Y").strftime("%Y-%m-%d")
        except Exception:
            state.start_date = min_date
            state.end_date = max_date

    return date_input, update_state


def render_video_card(v, show_clips_count):
    with (
        ui.card()
        .classes("cursor-pointer p-2 hover:shadow-xl transition-shadow border-gray-600")
        .on(
            "click",
            partial(navigate_to_film, v["video_id"], v.get("clip_id")),
        )
    ):
        with ui.row().classes("justify-between w-full"):
            ui.label(v["title"]).classes("truncate font-bold text-sm")
            ui.label(f"⏱ {v['duration_human']}").classes("text-xs")

        ui.label(f"🎭 {', '.join(v.get('partners', [])) or 'No partners'}").classes("text-xs")
        ui.label(f"🏷️ {', '.join(v.get('labels', [])) or 'No labels'}").classes("text-xs")
        ui.label(f"📂 {v['playlist_name']}").classes("text-xs text-primary")

        if show_clips_count:
            ui.label(f"🎬 {len(v.get('clips', []))}").classes("text-xs")


def render_media_page(
    *,
    title,
    data_loader,
    save_cliplist=None,
    user=None,
    show_save_button=False,
    show_clips_count=False,
):
    ui.label(title).classes("text-2xl font-bold mb-4 text-center")

    all_videos = data_loader()
    label = (m := re.search(r"🎬 (\w+),", title)) and m.group(1)

    all_playlists = sorted({v["playlist_name"] for v in all_videos})
    all_labels = sorted({l for v in all_videos for l in v.get("labels", [])})  # noqa: E741
    all_partners = sorted({p for v in all_videos for p in v.get("partners", [])})

    dates = [datetime.strptime(v["date"][:10], "%Y-%m-%d") for v in all_videos]
    min_date = min(dates).strftime("%Y-%m-%d") if dates else "1900-01-01"
    max_date = max(dates).strftime("%Y-%m-%d") if dates else "2100-01-01"

    state = MediaFilterState(all_playlists, min_date, max_date)

    with ui.splitter(horizontal=False, value=20).classes("w-full h-full rounded shadow") as splitter:
        # ---------------- FILTER PANEL ----------------
        with splitter.before:
            with ui.column().classes("w-full p-4 bg-gray-100 rounded-lg"):

                playlist_filter = (
                    ui.select(
                        options=all_playlists,
                        value=[],
                        label="Playlists (empty = all)",
                        multiple=True,
                        with_input=True,
                    )
                    .classes("w-full")
                    .props("use-chips")
                )

                label_qb, partner_qb = render_query_builders(all_labels, all_partners)
                ui.separator()

                _, update_dates = render_date_picker(min_date, max_date, state)

                def apply_filters():
                    state.page = 1
                    state.selected_playlists = playlist_filter.value
                    state.label_tokens = label_qb.tokens
                    state.partner_tokens = partner_qb.tokens
                    update_dates()
                    render_videos()

                def save_filters():
                    if not save_cliplist:
                        return
                    if not user:
                        caught_john_doe()
                        return

                    payload = state.to_cliplist_payload()

                    with ui.dialog() as dialog, ui.card():
                        name = ui.input("Cliplist Name")
                        lock = ui.checkbox("Lock Date Range", value=True)

                        def confirm():
                            if not lock.value:
                                payload["date_range"] = []
                            save_cliplist(name.value, payload, token=user.token)
                            ui.notify("✅ Saved", type="positive")
                            dialog.close()

                        ui.button("Save", on_click=confirm)

                    dialog.open()

                with ui.row().classes("justify-between"):
                    ui.button(icon="filter_alt", on_click=apply_filters)
                    if show_save_button:
                        ui.button(icon="save", on_click=save_filters)

        # ---------------- RESULTS PANEL ----------------
        with splitter.after:
            video_grid = ui.grid().classes(
                "grid auto-rows-max grid-cols-[repeat(auto-fit,minmax(250px,1fr))] gap-4 w-full p-4 bg-white"
            )
            pagination = (
                ui.pagination(
                    min=1,
                    max=1,
                    value=1,
                    direction_links=True,  # NiceGUI-supported
                )
                .props(
                    """
                    max-pages=5
                    boundary-numbers=false
                    boundary-links
                    input=false
                    ellipses=false
                    icon-first=first_page
                    icon-prev=chevron_left
                    icon-next=chevron_right
                    icon-last=last_page
                    """
                )
                .classes("mx-auto my-4")
            )

            def render_videos():
                filtered = state.apply(all_videos)
                filtered.sort(key=lambda v: v["date"], reverse=True)

                total_pages = max(1, (len(filtered) + state.VIDEOS_PER_PAGE - 1) // state.VIDEOS_PER_PAGE)

                pagination.max = total_pages
                pagination.value = min(state.page, total_pages)
                state.page = pagination.value

                start = (state.page - 1) * state.VIDEOS_PER_PAGE
                end = start + state.VIDEOS_PER_PAGE
                page_videos = filtered[start:end]

                video_grid.clear()
                with video_grid:
                    if not page_videos:
                        ui.label(f"No {label} found.").classes("col-span-full text-gray-400")
                        return

                    grouped = {}
                    for v in page_videos:
                        grouped.setdefault(v["date"][:10], []).append(v)

                    for day, vids in grouped.items():
                        human = datetime.strptime(day, "%Y-%m-%d").strftime("%B %d, %Y")
                        ui.label(f"🗓️ {human} ({len(vids)})").classes("text-xl font-semibold col-span-full")
                        for v in vids:
                            render_video_card(v, show_clips_count)

            pagination.on_value_change(
                lambda e: (
                    setattr(state, "page", e.value),
                    render_videos(),
                )
            )

            render_videos()

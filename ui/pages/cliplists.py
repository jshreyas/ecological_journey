from datetime import datetime

from nicegui import ui
from utils.utils_api import get_filtered_clips, load_cliplist


def cliplists_page():
    ui.label("🎬 Clips, Lists, and Cliplists!").classes(
        "text-2xl font-bold mb-4 text-center"
    )

    def render_filters():
        pass

    def render_media_grid_page(render_filters, render_grid):
        with ui.splitter(horizontal=False, value=0).classes(
            "w-full h-full rounded shadow"
        ) as splitter:
            with splitter.before:
                render_filters()
            with splitter.after:
                render_grid()

    def render_grid():
        video_grid = ui.grid().classes(
            "grid auto-rows-max grid-cols-[repeat(auto-fit,minmax(250px,1fr))] gap-4 w-full p-4 bg-white rounded-lg shadow-lg"
        )
        saved_cliplists = load_cliplist()
        with video_grid:
            for cliplist in saved_cliplists:
                with ui.card().classes(
                    "p-4 shadow-md bg-white rounded-lg border w-full"
                ):
                    with ui.row().classes("gap-2 w-full justify-between"):
                        ui.label(cliplist["name"]).classes("font-bold text-lg")
                        ui.button(
                            icon="play_arrow",
                            on_click=lambda c=cliplist: ui.navigate.to(
                                f'/playlist/{c["_id"]}'
                            ),
                        ).props("flat color=secondary").tooltip("Play")

                    operator_set = ["AND", "OR", "NOT"]
                    labels = cliplist["filters"].get("labels", [])
                    if labels:
                        html_parts = [
                            f'<span class="{"text-primary" if label in operator_set else "text-black"}">{label}</span>'
                            for label in labels
                        ]
                        ui.html(f'🏷️🔎 {" ".join(html_parts)}').classes("text-xs")
                    partners = cliplist["filters"].get("partners", [])
                    if partners:
                        html_parts = [
                            f'<span class="{"text-primary" if partner in operator_set else "text-black"}">{partner}</span>'
                            for partner in partners
                        ]
                        ui.html(f'🎭🔎 {" ".join(html_parts)}').classes("text-xs")
                    ui.label(
                        f"📂 {', '.join(cliplist['filters'].get('playlists', []))}"
                    ).classes("text-xs text-primary")
                    date_range = cliplist["filters"].get("date_range", [])
                    if date_range:
                        start = datetime.strptime(date_range[0], "%Y-%m-%d").strftime(
                            "%B %d, %Y"
                        )
                        end = datetime.strptime(date_range[1], "%Y-%m-%d").strftime(
                            "%B %d, %Y"
                        )
                        ui.label(f"🗓️ {start} to {end}").classes("text-xs text-primary")
                    filtered_videos = get_filtered_clips(cliplist["_id"])
                    total_duration = sum(
                        (v["end"] - v["start"])
                        for v in filtered_videos
                        if "start" in v and "end" in v
                    )
                    if total_duration:
                        if total_duration >= 3600:
                            total_duration_str = f"{total_duration // 3600}h {(total_duration % 3600) // 60}m {(total_duration % 60)}s"
                        elif total_duration >= 60:
                            total_duration_str = f"{(total_duration % 3600) // 60}m {(total_duration % 60)}s"
                        else:
                            total_duration_str = f"{total_duration % 60}s"
                    else:
                        total_duration_str = "0s"

                    with ui.row().classes("justify-between w-full items-center mt-2"):
                        ui.label(f"🎥 {len(filtered_videos)} clips").classes("text-xs")
                        ui.label(f"⏱️ {total_duration_str}").classes("text-xs")
        return video_grid

    render_media_grid_page(render_filters, render_grid)

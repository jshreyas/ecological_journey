from nicegui import ui
from utils_api import load_cliplist

def cliplists_page():
    ui.label("🎬 Cliplists!").classes('text-2xl font-bold mb-4 text-center')

    def render_filters():
        pass

    def render_media_grid_page(render_filters, render_grid):
        with ui.splitter(horizontal=False, value=0).classes('w-full h-full rounded shadow') as splitter:
            with splitter.before:
                render_filters()
            with splitter.after:
                render_grid()

    def render_grid():
        video_grid = ui.grid().classes(
            'grid auto-rows-max grid-cols-[repeat(auto-fit,minmax(250px,1fr))] gap-4 w-full p-4 bg-white rounded-lg shadow-lg'
        )
        saved_cliplists = load_cliplist()
        with video_grid:
            for cliplist in saved_cliplists:
                with ui.card().classes('p-4 shadow-md bg-white rounded-lg border w-full'):
                    with ui.row().classes("gap-2 w-full justify-between"):
                        ui.label(cliplist['name']).classes('font-bold text-lg')
                        ui.button(icon='play_arrow', on_click=lambda c=cliplist: ui.navigate.to(f'/cliplist/{c["_id"]}')).props('flat color=secondary').tooltip('Play')
                    ui.label(f"🏷️ {', '.join(cliplist['filters'].get('labels', []))}").classes('text-xs')
                    partners = cliplist['filters'].get('partners', [])
                    if partners:
                        ui.label(f"🎭 {', '.join(partners)}").classes('text-xs')
                    ui.label(f"📂 {', '.join(cliplist['filters'].get('playlists', []))}").classes('text-xs text-primary')
        return video_grid

    render_media_grid_page(render_filters, render_grid)
# film.py
import os
from datetime import datetime

from dotenv import load_dotenv
from nicegui import ui
from pages.components.film.anchor_tab import AnchorTab
from pages.components.film.anchorboard_tab import AnchorboardTab
from pages.components.film.clipboard_tab import ClipboardTab
from pages.components.film.filmboard_tab import FilmboardTab
from pages.components.film.learnings_tab import LearningsTab
from pages.components.film.metaforge_tab import MetaforgeTab
from pages.components.film.navigation_tab import NavigationTab
from pages.components.film.player_controls_tab import PlayerControlsTab
from pages.components.film.share_dialog_tab import ShareDialogTab
from pages.components.film.video_state import VideoState
from utils.user_context import User, with_user_context

load_dotenv()


BASE_URL_SHARE = os.getenv("BASE_URL_SHARE")


# TODO: Make this page mobile friendly for logged in user for write access
@with_user_context
def film_page(user: User | None, video_id: str):
    # Initialize VideoState for centralized state management
    video_state = VideoState(video_id, user)

    query_params = ui.context.client.request.query_params
    clip_id = query_params.get("clip")
    play_clips_playlist = query_params.get("clips", "false").lower() == "true"
    autoplay_clip = None
    if clip_id:
        video = video_state.get_video()
        if not video:
            ui.label(f"⚠️ Video: {video_id} not found!")
            return
        clips = video.get("clips", [])
        autoplay_clip = next((c for c in clips if c["clip_id"] == clip_id), None)
        if not autoplay_clip:
            ui.label(f"⚠️ Clip: {clip_id} not found in video {video_id}!")
            return
        video_id = autoplay_clip.get("video_id", video_id)
        # Reinitialize video_state if video_id changed
        if video_id != video_state.video_id:
            video_state = VideoState(video_id), user

    # Initialize components with user
    navigation_tab = NavigationTab(video_state)
    player_controls_tab = PlayerControlsTab(video_state)
    share_dialog_tab = ShareDialogTab(video_state)
    # TODO: cleanup user from all tabs since video_state has it
    metaforge_tab = MetaforgeTab(video_state, user)
    filmboard_tab = FilmboardTab(video_state)
    learnings_tab = LearningsTab(video_state, user)
    anchor_tab = AnchorTab(video_state)

    clipboard_tab = ClipboardTab(
        video_state,
        on_play_clip=player_controls_tab.play_clip,
        on_share_clip=share_dialog_tab.share_clip,
    )
    anchorboard_tab = AnchorboardTab(
        video_state,
        on_play_anchor=player_controls_tab.play_at_time,
    )

    # Inline render_film_editor functionality
    with ui.column().classes("w-full"):
        # Navigation
        with ui.row().classes("w-full justify-between items-center") as navigation_container:
            navigation_tab.create_tab(navigation_container)

        with ui.splitter(horizontal=False, value=70).classes("w-full h-[70vh] rounded shadow") as splitter:
            with splitter.before:
                with ui.column().classes("w-full h-full") as player_container_ref:
                    player_controls_tab.create_tab(player_container_ref, play_clips_playlist, autoplay_clip)
            with splitter.after:
                with ui.tabs().classes("w-full") as tabs:
                    one = ui.tab("Metadata", label="", icon="description").classes("w-full")
                    two = ui.tab("Learnings", label="", icon="chat").classes("w-full")
                    three = ui.tab("Clipboard", label="", icon="video_library").classes("w-full")
                    four = ui.tab("Anchorboard", label="", icon="bookmark").classes("w-full")
                    five = ui.tab("Control Panel", label="", icon="settings").classes("w-full")
                with ui.tab_panels(tabs, value=four).classes("w-full h-full"):
                    with ui.tab_panel(one):
                        metaforge_container = ui.scroll_area().classes("absolute w-full h-full top-0 left-0")
                        metaforge_tab.create_tab(metaforge_container)
                    with ui.tab_panel(two):
                        chat_container = ui.scroll_area().classes("absolute w-full h-full top-0 left-0")
                        learnings_tab.create_tab(chat_container)
                    with ui.tab_panel(three):
                        clipboard_container = ui.scroll_area().classes("absolute w-full h-full top-0 left-0")
                        clipboard_tab.create_tab(clipboard_container, clip_id)
                    with ui.tab_panel(four):
                        anchorboard_container = ui.scroll_area().classes("absolute w-full h-full top-0 left-0")
                        anchorboard_tab.create_tab(anchorboard_container)
                    with ui.tab_panel(five) as anchortab_container:
                        anchor_tab.create_tab(anchortab_container)
                video_state.tabber = tabs
            with splitter.separator:
                ui.icon("drag_indicator").classes("text-gray-400")

        ui.separator().classes("w-full mt-2")
        # Filmboard heading with count
        current_video_date = filmboard_tab.get_current_video_date()
        same_day_count = filmboard_tab.get_same_day_videos_count()
        with ui.column().classes("w-full h-full rounded-lg"):
            if current_video_date:
                ui.label(
                    f'🎥 More films from 🗓️ {datetime.strptime(current_video_date, "%Y-%m-%d").strftime("%B %d, %Y")} ({same_day_count + 1})'
                ).classes("text-xl ml-2 font-semibold")
            else:
                ui.label("🎥 More films from the same day").classes("text-xl ml-2 font-semibold")
            with ui.grid().classes(
                "grid auto-rows-max grid-cols-[repeat(auto-fit,minmax(250px,1fr))] w-full p-2 bg-white rounded-lg shadow-lg"
            ) as filmboard_container:
                filmboard_tab.create_tab(filmboard_container)

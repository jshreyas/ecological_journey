# film.py
import os

from dotenv import load_dotenv
from nicegui import ui

from ui.pages.components.film.learnings_tab import LearningsTab
from ui.pages.components.film.matadata_tab import MatadataTab
from ui.pages.components.film.player_controls_tab import PlayerControlsTab
from ui.pages.components.film.share_dialog_tab import ShareDialogTab
from ui.pages.components.film.timeline_tab import TimelineTab
from ui.pages.components.film.video_state import VideoState
from ui.utils.user_context import User, with_user_context

load_dotenv()


BASE_URL_SHARE = os.getenv("BASE_URL_SHARE")


# TODO: Make this page mobile friendly for logged in user for write access
@with_user_context
def film_page(user: User | None, video_id: str):
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

    player_controls_tab = PlayerControlsTab(video_state)
    share_dialog_tab = ShareDialogTab(video_state)
    learnings_tab = LearningsTab(video_state)
    metadata_tab = MatadataTab(
        video_state,
        on_play_anchor=player_controls_tab.play_at_time,
        on_play_clip=player_controls_tab.play_clip,
        on_share_clip=share_dialog_tab.share_clip,
    )
    timeline_tab = TimelineTab(
        video_state,
    )

    with ui.column().classes("w-full"):
        with ui.splitter(horizontal=False, value=70).classes("w-full h-[80vh] rounded shadow") as splitter:
            with splitter.before:
                with ui.column().classes("w-full h-full") as player_container_ref:
                    player_controls_tab.create_tab(player_container_ref, play_clips_playlist, autoplay_clip)
            with splitter.after:
                with ui.tabs().classes("w-full") as tabs:
                    timeline = ui.tab("Timeline", icon="timeline").classes("w-full bg-primary text-black")
                    two = ui.tab("Learnings", label="", icon="chat").classes("w-full bg-primary text-black")
                    five = ui.tab("Control Panel", label="", icon="bookmarks").classes("w-full bg-primary text-black")
                with ui.tab_panels(tabs, value=five).classes("w-full h-full"):
                    with ui.tab_panel(timeline):
                        timeline_container = ui.column().classes("w-full h-full")
                        timeline_tab.create_tab(timeline_container)
                    with ui.tab_panel(two):
                        chat_container = ui.scroll_area().classes("absolute w-full h-full top-0 left-0")
                        learnings_tab.create_tab(chat_container)
                    with ui.tab_panel(five) as metadata_tab_container:
                        metadata_tab.create_tab(metadata_tab_container)
                video_state.tabber = tabs
            with splitter.separator:
                ui.icon("drag_indicator").classes("text-gray-400")

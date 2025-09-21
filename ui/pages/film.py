# film.py
import os
from datetime import datetime

from dotenv import load_dotenv
from nicegui import ui
from pages.components.film.clipboard_tab import ClipboardTab
from pages.components.film.filmboard_tab import FilmboardTab
from pages.components.film.metaforge_tab import MetaforgeTab
from pages.components.film.navigation_tab import NavigationTab
from pages.components.film.player_controls_tab import PlayerControlsTab
from pages.components.film.share_dialog_tab import ShareDialogTab
from pages.components.film.video_state import VideoState
from utils.dialog_puns import in_progress
from utils.user_context import User, with_user_context
from utils.utils_api import load_video

load_dotenv()


BASE_URL_SHARE = os.getenv("BASE_URL_SHARE")


# TODO: Make this page mobile friendly for logged in user for write access
@with_user_context
def film_page(user: User | None, video_id: str):
    # Initialize VideoState for centralized state management
    video_state = VideoState(video_id)

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
            video_state = VideoState(video_id)

    # Initialize components with user
    navigation_tab = NavigationTab(video_state)
    player_controls_tab = PlayerControlsTab(video_state)
    share_dialog_tab = ShareDialogTab(video_state)
    metaforge_tab = MetaforgeTab(video_state, user)
    filmboard_tab = FilmboardTab(video_state)

    clipboard_tab = ClipboardTab(
        video_state,
        on_play_clip=player_controls_tab.play_clip,
        on_share_clip=share_dialog_tab.share_clip,
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
                    one = ui.tab("Metadata").classes("w-full")
                    two = ui.tab("Learnings").classes("w-full")
                with ui.tab_panels(tabs, value=one).classes("w-full"):
                    with ui.tab_panel(one):
                        with ui.column().classes("w-full h-full") as metaforge_container:
                            metaforge_tab.create_tab(metaforge_container)
                    with ui.tab_panel(two):
                        # --- Fake stub conversation ---
                        current_user = {"id": "u1", "name": "You"}

                        conversation = [
                            {
                                "author_id": "u1",
                                "author_name": "You",
                                "text": "Hey team, let's review today's clips.",
                                "stamp": "10:00",
                            },
                            {
                                "author_id": "u2",
                                "author_name": "Alice",
                                "text": "Sounds good, I’ll upload mine soon.",
                                "stamp": "10:02",
                            },
                            {
                                "author_id": "u3",
                                "author_name": "Bob",
                                "text": "I clipped yesterday’s sparring, check it out!",
                                "stamp": "10:05",
                            },
                            {
                                "author_id": "u1",
                                "author_name": "You",
                                "text": "Nice — I’ll add some comments there.",
                                "stamp": "10:06",
                            },
                        ]

                        toolbar = [
                            [
                                "bold",
                                "italic",
                                "strike",
                                "underline",
                                "unordered",
                                "ordered",
                                "quote",
                                "undo",
                                "redo",
                                "removeFormat",
                                "fullscreen",
                                "viewsource",
                            ],
                        ]

                        # --- UI ---
                        with ui.card().classes("w-full h-[600px] flex flex-col"):
                            with ui.scroll_area().classes("w-full flex-1 overflow-y-auto"):
                                for msg in conversation:
                                    ui.chat_message(
                                        text=msg["text"],
                                        name=msg["author_name"],
                                        stamp=msg["stamp"],
                                        sent=(msg["author_id"] == current_user["id"]),
                                        text_html=True,
                                    ).classes("w-full")
                                with ui.expansion("✍️").classes("w-full"):
                                    with ui.row().classes("w-full border-t"):
                                        text_input = ui.editor(placeholder="Type your learnings...").classes(
                                            "flex-grow"
                                        )
                                        text_input.props["toolbar"] = toolbar
                                        ui.button(icon="send", on_click=in_progress).classes(
                                            "absolute bottom-0 right-0"
                                        )
            with splitter.separator:
                ui.icon("drag_indicator").classes("text-gray-400")

        ui.separator().classes("w-full mt-2")
        with ui.splitter(value=50).classes("w-full h-[600px]") as splitter:
            with splitter.before:
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
            with splitter.after:
                # Clipboard heading with count
                video = load_video(video_id)
                clips = video.get("clips", [])
                with ui.column().classes("w-full h-full rounded-lg"):
                    ui.label(f"📋 Clipboard ({len(clips)})").classes("text-xl font-semibold ml-2")
                    with ui.grid().classes(
                        "grid auto-rows-max grid-cols-[repeat(auto-fit,minmax(250px,1fr))] w-full p-2 bg-white rounded-lg shadow-lg"
                    ) as clipboard_container:
                        clipboard_tab.create_tab(clipboard_container, clip_id)


def chips_input_combined(initial=None):
    """Single chips input for both partners (@) and labels (#)."""
    initial = initial or []
    chips_list = initial.copy()
    container = ui.row().classes("gap-2")
    input_ref = ui.input("Add @partner or #label").classes("w-full").props("dense")
    error_label = ui.label().classes("text-red-500 text-xs")

    def add_chip():
        val = input_ref.value.strip()
        if not val:
            return
        if not (val.startswith("@") or val.startswith("#")):
            error_label.text = "Start with @ for partners or # for labels"
            return
        if val in chips_list:
            error_label.text = "Already added"
            return
        error_label.text = ""
        chips_list.append(val)
        with container:
            ui.chip(
                val,
                icon="person" if val.startswith("@") else "label",
                color="secondary" if val.startswith("@") else "primary",
                removable=True,
            ).on("remove", lambda e, v=val: chips_list.remove(v))
        input_ref.value = ""

    input_ref.on("keydown.enter", add_chip)
    with input_ref.add_slot("append"):
        ui.button(icon="add", on_click=add_chip).props("round dense flat")
    # Render initial chips
    with container:
        for val in chips_list:
            ui.chip(
                val,
                icon="person" if val.startswith("@") else "label",
                color="secondary" if val.startswith("@") else "primary",
                removable=True,
            ).on("remove", lambda e, v=val: chips_list.remove(v))
    return input_ref, chips_list, error_label, container

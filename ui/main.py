import asyncio
import logging
import os
import sys
import time
from typing import Annotated, Any, Dict, List

import httpx
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from nicegui import app, ui
from starlette.responses import RedirectResponse
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from ui.data.auth import require_api_user
from ui.data.crud import (
    add_video_to_playlist,
    clear_cache,
    create_access_token,
    delete_videos_from_playlist,
    get_or_create_user,
    load_playlist,
    load_playlists,
    load_teams,
    trigger_notion_refresh,
)
from ui.data.models import User
from ui.log import log
from ui.pages.about import about_page
from ui.pages.cliplists import cliplists_page
from ui.pages.custom_sub_pages import custom_sub_pages
from ui.pages.film import film_page
from ui.pages.home import home_page
from ui.pages.notion import notion_page
from ui.pages.playlist import playlist_page
from ui.pages.search import search_page
from ui.utils.user_context import get_current_user
from ui.utils.youtube import fetch_playlist_items

load_dotenv()
sys.stdout.reconfigure(line_buffering=True)

oauth = OAuth()

oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    client_kwargs={"scope": "openid email profile"},
)


@app.get("/auth/google/login")
async def google_login(request: Request):
    post_login_path = request.query_params.get("post_login_path", "/")

    return await oauth.google.authorize_redirect(
        request,
        request.url_for("google_oauth"),
        state=post_login_path,
    )


def _is_valid(user_info: dict) -> bool:
    try:
        return all(
            [
                int(user_info.get("exp", 0)) > int(time.time()),
                user_info.get("aud") == os.getenv("GOOGLE_CLIENT_ID"),
                user_info.get("iss") in {"https://accounts.google.com", "accounts.google.com"},
                str(user_info.get("email_verified")).lower() == "true",
            ]
        )
    except Exception:
        return False


@app.get("/auth/google/callback")
async def google_oauth(request: Request) -> RedirectResponse:
    redirect_path = request.query_params.get("state") or "/"

    try:
        token = await oauth.google.authorize_access_token(request)

        user_info = token.get("userinfo") or {}

        if not _is_valid(user_info):
            logging.warning("Google OAuth callback received invalid user information")
            return RedirectResponse(redirect_path)

        email = user_info["email"]
        username = user_info.get("name") or user_info.get("given_name") or email.split("@", maxsplit=1)[0]

        user = get_or_create_user(
            email=email,
            username=username,
            oauth_provider="google",
            oauth_sub=user_info["sub"],
        )

        jwt_token = create_access_token({"sub": str(user.id)})

        app.storage.user.clear()
        app.storage.user.update(
            {
                "authenticated": True,
                "user_id": str(user.id),
                "token": jwt_token,
                "google_access_token": token.get("access_token"),
            }
        )

    except Exception as exc:
        logging.exception("OAuth failed with exception: %s", exc)

    return RedirectResponse(redirect_path)


api_router = APIRouter()


@api_router.get("/teams")
def get_teams():
    return load_teams()


@api_router.get("/playlists")
def get_playlists(full: bool = True):
    if full:
        return [load_playlist(p["_id"]) for p in load_playlists()]
    return load_playlists()


@api_router.post("/playlists/{playlist_id}/videos")
def post_playlist_videos(
    playlist_id: str,
    new_videos: list[dict[str, Any]],
    user: Annotated[User, Depends(require_api_user)],
):
    return add_video_to_playlist(
        playlist_id=playlist_id,
        new_videos=new_videos,
        user=user,
    )


@api_router.delete("/playlists/{playlist_id}/videos")
def delete_playlist_videos(
    playlist_id: str,
    payload: Dict[str, List[str]],
    user: Annotated[User, Depends(require_api_user)],
):
    video_ids = payload.get("video_ids", [])

    if not video_ids:
        return {
            "_id": playlist_id,
            "deleted_count": 0,
            "videos": [],
        }

    return delete_videos_from_playlist(
        playlist_id=playlist_id,
        video_ids=video_ids,
        user=user,
    )


app.include_router(api_router, prefix="/api")


def setup_landscape_mode_guard():
    """Show a mobile portrait warning overlay and auto-hide in landscape."""

    ui.add_head_html(
        """
        <style>
        #portrait-overlay {
            display: none;
        }
        @media (max-width: 1024px) and (orientation: portrait) {
            #portrait-overlay {
                display: flex;
            }
        }
        </style>
    """
    )

    overlay = (
        ui.element("div")
        .props('id="portrait-overlay"')
        .classes(
            """
        fixed inset-0
        z-[9999]
        items-center
        justify-center
        bg-black/50
        """
        )
    )
    with overlay:
        with ui.card(align_items="center").classes("w-11/12 max-w-sm"):
            ui.icon("screen_rotation").classes("text-4xl")
            ui.label("This application is optimized for landscape mode.").classes("text-center text-base")
            ui.label("Rotate your device for the best experience.").classes("text-center text-base")


# TODO: move this and playlist sync code to its own file?
class LogElementHandler(logging.Handler):
    """Push logging records into one NiceGUI ui.log element."""

    def __init__(self, element: ui.log, level: int = logging.NOTSET) -> None:
        super().__init__(level)
        self.element = element

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            self.element.push(message)
        except Exception:
            self.handleError(record)


@ui.page("/")
@ui.page("/{_:path}")
async def main_page() -> None:
    log.info("Rendering main page")
    ui.add_head_html(
        """
        <script src="https://www.youtube.com/iframe_api"></script>
        """
    )
    setup_landscape_mode_guard()
    with ui.header().classes(
        "top-navbar flex items-center justify-between h-14 px-4 py-2 bg-primary fixed top-0 z-50 w-full shadow-sm"
    ):

        def nav_button(label: str, path: str):
            return (
                ui.button(label, on_click=lambda: ui.navigate.to(path))
                .classes("text-white text-base normal-case px-4 py-1")
                .props("flat dense")
            )

        def nav_icon(icon: str, path: str):
            return (
                ui.button(icon=icon, on_click=lambda: ui.navigate.to(path))
                .classes("text-white text-base normal-case px-4 py-1")
                .props("flat dense")
            )

        with ui.button_group().classes("gap-1 items-center justify-center border-none shadow-none"):
            nav_icon("home", "/")
            nav_icon("search", "/search")
            nav_icon("description", "/notion")
            nav_icon("info", "/about")
            # nav_button("Cliplists", "/cliplists")

        ui.space()

        auth_container = ui.row().classes("items-center")  # Container for login/logout buttons and user info

        def render_auth():
            auth_container.clear()
            user = get_current_user()
            # authenticated = app.storage.user.get("authenticated", False)

            with auth_container:
                if user is None:

                    def login():
                        app.storage.user.setdefault("init", True)
                        ui.run_javascript(
                            """
                            const path = window.location.pathname + window.location.search;
                            window.location.href = "/auth/google/login?post_login_path=" + encodeURIComponent(path);
                        """
                        )

                    ui.button(
                        icon="login",
                        on_click=login,
                    ).classes(
                        "text-white"
                    ).props("flat round dense")
                    return

                ui.label(f"Hi, {user.username}!").classes("text-sm text-white")
                # TODO: add a super admin role instead of these hardcoded checks

                if user.email == "shreyas.jukanti@gmail.com":
                    with ui.fab("settings", label="", direction="down").classes("px-1").props("fab-mini padding=0"):

                        async def playlistss():
                            state = {
                                "reload_on_close": False,
                            }

                            async def close_dialog() -> None:
                                dialog.close()

                                if state["reload_on_close"]:
                                    await asyncio.sleep(0)
                                    ui.navigate.reload()

                            with (
                                ui.dialog().props("persistent") as dialog,
                                ui.card().classes("w-full max-w-3xl relative"),
                            ):
                                log_element = ui.log(max_lines=200).classes("w-full h-96 font-mono text-sm")

                                close_button = ui.button(
                                    "Close",
                                    on_click=close_dialog,
                                ).props("flat")

                                close_button.disable()

                            dialog.open()

                            handler = LogElementHandler(log_element)
                            handler.setFormatter(
                                logging.Formatter(
                                    fmt="%(asctime)s %(levelname)s: %(message)s",
                                    datefmt="%H:%M:%S",
                                )
                            )

                            sync_logger = logging.getLogger(f"playlist-sync-{id(dialog)}")
                            sync_logger.setLevel(logging.INFO)
                            sync_logger.propagate = False
                            sync_logger.addHandler(handler)

                            ui.context.client.on_disconnect(lambda: sync_logger.removeHandler(handler))

                            try:
                                playlists = [load_playlist(p["_id"]) for p in load_playlists()]

                                sync_logger.info(
                                    "Starting sync for %s playlists.",
                                    len(playlists),
                                )

                                videos_to_sync = await fetch_playlist_items(
                                    playlists,
                                    logger=sync_logger,
                                )

                                sync_logger.info(
                                    "Fetch result contains %s playlists.",
                                    len(videos_to_sync),
                                )

                                total_videos = sum(len(videos) for videos in videos_to_sync.values())

                                sync_logger.info(
                                    "Total videos available for synchronization: %s",
                                    total_videos,
                                )

                                if total_videos == 0:
                                    sync_logger.info(
                                        "No videos to synchronize. "
                                        "You can close this dialog; the page will not reload."
                                    )
                                    return

                                sync_logger.info("Starting synchronization of videos to playlists...")

                                for playlist_id, videos in videos_to_sync.items():
                                    add_video_to_playlist(
                                        playlist_id=playlist_id,
                                        new_videos=videos,
                                        user=user,
                                    )

                                    sync_logger.info(
                                        "Synchronized %s videos to playlist %s.",
                                        len(videos),
                                        playlist_id,
                                    )

                                state["reload_on_close"] = True

                                sync_logger.info(
                                    "Synchronization completed successfully. " "Close this dialog to reload the page."
                                )
                            except asyncio.CancelledError:
                                sync_logger.warning("Sync cancelled. You can now close the dialog.")
                                raise
                            except Exception:
                                sync_logger.exception(
                                    "Sync failed. You can close the dialog; " "the page will not reload."
                                )
                            finally:
                                close_button.enable()

                                sync_logger.removeHandler(handler)
                                handler.close()

                        ui.fab_action("playlist_add_check", on_click=lambda: playlistss())

                        def notion_tree_update():
                            trigger_notion_refresh()
                            ui.notify("Started Notion tree sync in background")

                        ui.fab_action("description", on_click=lambda: notion_tree_update())

                        def clearc():
                            clear_cache(user=user)
                            ui.notify("Cache cleared successfully!", color="green")
                            ui.navigate.reload()

                        ui.fab_action("delete", on_click=lambda: clearc())

                ui.button(icon="logout", on_click=handle_logout).props("flat round dense color=red")

        async def handle_logout():
            access_token = app.storage.user.get("google_access_token")

            if access_token:
                try:
                    async with httpx.AsyncClient() as client:
                        await client.post(
                            "https://oauth2.googleapis.com/revoke",
                            params={"token": access_token},
                            headers={
                                "content-type": "application/x-www-form-urlencoded",
                            },
                        )
                except Exception:
                    logging.exception("Failed to revoke Google token")

            app.storage.user.clear()
            app.storage.user["authenticated"] = False

            render_auth()
            ui.navigate.reload()

        render_auth()

    custom_sub_pages(
        {
            "/": home_page,
            "/about": about_page,
            "/search": search_page,
            "/cliplists": cliplists_page,
            "/film/{video_id}": film_page,
            "/notion": notion_page,  # TODO: the embed doesnt work
            # "/stories": stories,
            "/playlist/{cliplist_id}": playlist_page,
        }
    ).classes("w-full h-full flex-grow p-4")


OBSERVABLE_URL = os.getenv("OBSERVABLE_URL")


# TODO: this doesnt work
# def stories():
#     ui.html(
#         f"""
#         <iframe src="{OBSERVABLE_URL}"
#                 style="width:100%; height:110vh; border:none;"></iframe>
#     """
#     ).classes("w-full h-full")


app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")


ui.run(
    title="Ecological Journey",
    reload=True if os.getenv("ENV") == "dev" else False,
    storage_secret="45d3fba306d5a694f61d0ccd684c75fa",
    reconnect_timeout=30,
)

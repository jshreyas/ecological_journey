import logging
import os
import sys
import time
from typing import Any, Dict, List

from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
from fastapi import APIRouter, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from nicegui import app, ui
from starlette.responses import RedirectResponse

from ui.data.crud import (
    add_video_to_playlist,
    clear_cache,
    create_access_token,
    get_or_create_user,
    load_playlist,
    load_playlists,
    load_teams,
)
from ui.pages.about import about_page
from ui.pages.cliplists import cliplists_page
from ui.pages.clips import clips_page
from ui.pages.custom_sub_pages import custom_sub_pages
from ui.pages.film import film_page
from ui.pages.home import home_page

# from ui.pages.notion import notion_page
from ui.pages.partner import partner_page
from ui.pages.playlist import playlist_page
from ui.pages.search import search_page

# TODO: missing @api_router apis and check sync playlist works
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
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo", {})

        if _is_valid(user_info):
            user = get_or_create_user(
                user_info["email"],
                user_info["name"],
                "google",
                user_info["sub"],
            )

            jwt_token = create_access_token({"sub": str(user["_id"])})

            app.storage.user.update(
                {
                    "authenticated": True,
                    "user": user_info["name"],
                    "id": str(user["_id"]),
                    "token": jwt_token,
                    "user_info": user_info,
                }
            )
            clear_cache()

    except Exception:
        logging.exception("OAuth failed")

    redirect_path = request.query_params.get("state") or "/"
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
    new_videos: List[Dict[str, Any]],
    authorization: str = Header(...),
):
    if not authorization.startswith("Bearer "):
        raise Exception("Invalid auth header")

    token = authorization.removeprefix("Bearer ").strip()

    return add_video_to_playlist(
        playlist_id=playlist_id,
        new_videos=new_videos,
        token=token,
    )


# app.mount("/api", api_router)
app.include_router(api_router, prefix="/api")


@ui.page("/")
@ui.page("/{_:path}")
async def main_page() -> None:
    with ui.header().classes(
        "top-navbar flex items-center justify-between px-4 py-2 bg-primary fixed top-0 z-50 w-full shadow-sm"
    ):

        def nav_button(label: str, path: str):
            return (
                ui.button(label, on_click=lambda: ui.navigate.to(path))
                .classes("text-white text-base normal-case px-4 py-1")
                .props("flat dense")
            )

        with ui.button_group().classes("gap-1 items-center justify-center border-none shadow-none"):
            ui.button(icon="home", on_click=lambda: ui.navigate.to("/")).classes(
                "text-white text-base normal-case px-4 py-1"
            ).props("flat dense")
            nav_button("Search", "/search")
            nav_button("Clips", "/clips")
            nav_button("Cliplists", "/cliplists")
            nav_button("About", "/about")
            # nav_button("Notion", "/notion")

        ui.space()

        auth_container = ui.row().classes("items-center")  # Container for login/logout buttons and user info

        def render_auth():
            auth_container.clear()
            authenticated = app.storage.user.get("authenticated", False)

            with auth_container:
                if not authenticated:

                    def login():
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
                else:
                    user = app.storage.user.get("user_info", {}).get("name")
                    ui.label(f"Hi, {user}!").classes("text-sm text-white")
                    ui.button(icon="logout", on_click=handle_logout).props("flat round dense color=red")

        def handle_logout():
            app.storage.user.clear()
            app.storage.user.update({"authenticated": False})
            render_auth()
            ui.navigate.to("/")

        render_auth()

    custom_sub_pages(
        {
            "/": home_page,
            "/about": about_page,
            "/search": search_page,
            "/clips": clips_page,
            "/cliplists": cliplists_page,
            "/film/{video_id}": film_page,
            # "/notion": notion_page,  # TODO: the embed doesnt work
            "/partners": partner_page,
            # "/stories": stories,
            "/playlist/{cliplist_id}": playlist_page,
        }
    ).classes("w-full h-full flex-grow p-4")


OBSERVABLE_URL = os.getenv("OBSERVABLE_URL")


# TODO: this doesnt work
def stories():
    ui.html(
        f"""
        <iframe src="{OBSERVABLE_URL}"
                style="width:100%; height:110vh; border:none;"></iframe>
    """
    ).classes("w-full h-full")


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
    reload=True,
    storage_secret="45d3fba306d5a694f61d0ccd684c75fa",
)

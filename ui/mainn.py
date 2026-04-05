import logging
import os
import sys
import time

from authlib.integrations.starlette_client import OAuth, OAuthError
from dotenv import load_dotenv
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from nicegui import app, ui
from starlette.responses import RedirectResponse

from ui.pages.about import about_page
from ui.pages.cliplists import cliplists_page
from ui.pages.clips import clips_page
from ui.pages.custom_sub_pages import custom_sub_pages, protected
from ui.pages.film import film_page
from ui.pages.home import home_page
from ui.pages.notion import notion_page
from ui.pages.partner import partner_page
from ui.pages.playlist import playlist_page
from ui.pages.search import search_page

# TODO: missing @api_router apis and check sync playlist works
load_dotenv()
FRONTEND_URL = os.getenv("BASE_URL_SHARE")
sys.stdout.reconfigure(line_buffering=True)

oauth = OAuth()

oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    client_kwargs={"scope": "openid email profile"},
    redirect_uri=f"{FRONTEND_URL}/auth/google/callback",
)


@app.get("/auth/google/login")
async def google_login(request: Request):
    post_login_path = request.query_params.get("post_login_path", "/")
    redirect_uri = f"{FRONTEND_URL}/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri, state=post_login_path)


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
            app.storage.user["user_info"] = user_info
            app.storage.user["authenticated"] = True

        # 🔥 get redirect path from state
        redirect_path = request.query_params.get("state") or "/"

    except (OAuthError, Exception):
        logging.exception("could not authorize access token")
        redirect_path = "/"

    return RedirectResponse(redirect_path)


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
            nav_button("Notion", "/notion")

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
            "/notion": notion_page,  # TODO: the embed doesnt work
            "/partners": partner_page,
            "/stories": stories,
            "/playlist/{cliplist_id}": playlist_page,
            "/secret": secret,
            "/error": error,
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


def home():
    ui.markdown(
        """
        This example shows inheritance from `ui.sub_pages` for decorator-based route protection and a custom 404 page.

        **Try it:** Navigate to "Secret" (passphrase: "spa") or "Invalid" for 404.
    """
    )


def error():
    raise ValueError("some error message")


@protected
def secret():
    ui.markdown(
        """
        ### Secret Area 🔑

        This is confidential information only for authenticated users.
    """
    )


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

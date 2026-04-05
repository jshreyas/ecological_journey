import logging
import os
import time

from authlib.integrations.starlette_client import OAuth, OAuthError
from dotenv import load_dotenv
from fastapi import Request
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

load_dotenv()
FRONTEND_URL = os.getenv("BASE_URL_SHARE")


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
        redirect_path = request.query_params.get("state", "/")

    except (OAuthError, Exception):
        logging.exception("could not authorize access token")
        redirect_path = "/"

    return RedirectResponse(redirect_path)


@ui.page("/")
@ui.page("/{_:path}")
async def main_page() -> None:
    with ui.header().classes("items-center bg-blue-100"):
        ui.button("Home", on_click=lambda: ui.navigate.to("/")).props("flat")
        ui.button("Search", on_click=lambda: ui.navigate.to("/search")).props("flat")
        ui.button("Clips", on_click=lambda: ui.navigate.to("/clips")).props("flat")
        ui.button("Cliplists", on_click=lambda: ui.navigate.to("/cliplists")).props("flat")
        ui.button("About", on_click=lambda: ui.navigate.to("/about")).props("flat")
        ui.button("Notion", on_click=lambda: ui.navigate.to("/notion")).props("flat")
        ui.space()

        auth_container = ui.row().classes("items-center")  # Container for login/logout buttons and user info

        def render_auth():
            auth_container.clear()
            authenticated = app.storage.user.get("authenticated", False)

            with auth_container:
                if not authenticated:
                    ui.button(
                        icon="login",
                        on_click=lambda: ui.navigate.to(
                            f"/auth/google/login?post_login_path={ui.context.client.request.url.path}"
                        ),
                    ).props("flat round dense color=primary")
                else:
                    ui.label("Hi, me!").classes("text-sm text-primary")
                    ui.button(icon="logout", on_click=handle_logout).props("flat round dense color=primary")

        def handle_logout():
            app.storage.user.clear()
            render_auth()
            ui.navigate.to("/about")

        render_auth()

    custom_sub_pages(
        {
            "/": home_page,
            "/about": about_page,
            "/search": search_page,
            "/clips": clips_page,
            "/cliplists": cliplists_page,
            "/film/{video_id}": film_page,
            "/notion": notion_page,
            "/partners": partner_page,
            "/playlist/{cliplist_id}": playlist_page,
            "/secret": secret,
            "/error": error,
        }
    ).classes("flex-grow p-4")


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


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(storage_secret="demo_secret_key_change_in_production")

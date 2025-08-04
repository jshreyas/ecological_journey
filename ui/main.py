import os
import sys

from authlib.integrations.starlette_client import OAuth, OAuthError
from data.crud import clear_cache, create_access_token, create_feedback, get_or_create_user, login_user
from dotenv import load_dotenv
from fastapi import Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from nicegui import app, ui
from pages.about import about_page
from pages.cliplists import cliplists_page
from pages.clips import clips_page
from pages.film import film_page
from pages.films import films_page
from pages.home import home_page
from pages.notion import notion_page
from pages.partner import partner_page
from pages.playlist import playlist_page
from utils.dialog_puns import caught_john_doe, handle_backend_error

sys.stdout.reconfigure(line_buffering=True)

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL")
# TODO: is there a way to get rid of app.storage.user usage and use some version of @with_user_context instead?


def google_login_button():
    with (
        ui.button("", on_click=open_google_login_dialog)
        .props("outline")
        .classes("items-center text-sm hover:bg-gray-100")
    ):

        with (
            ui.element("div")
            .classes("q-icon notranslate")
            .style("width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;")
        ):
            ui.html(
                """
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" style="width:20px; height:20px;">
                <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0
                14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58
                2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92
                16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15
                1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98
                6.19C6.51 42.62 14.62 48 24 48z"/>
                <path fill="none" d="M0 0h48v48H0z"/>
            </svg>
            """
            )


def login_or_signup(mode="login"):
    with (
        ui.dialog() as dialog,
        ui.card().style("padding: 2rem; max-width: 400px; width: 90vw;").classes("w-full"),
    ):
        with ui.row().classes("justify-between items-center w-full"):
            ui.label(f"{'Login' if mode == 'login' else 'Register'}").classes("text-xl font-bold")
            with ui.row().classes("justify-end items-center"):
                ui.button(icon="person_add", on_click=lambda: caught_john_doe())
                google_login_button()

        with ui.column().classes("gap-4 w-full"):
            email = ui.input("Email").classes("w-full")
            password = ui.input("Password", password=True).classes("w-full")

        with ui.row().classes("justify-center gap-4 mt-6 w-full"):
            ui.button(icon="send", on_click=lambda: submit())
            ui.button(icon="close", on_click=dialog.close)

        def submit():
            waiting_dialog = ui.dialog().props("persistent")
            with waiting_dialog:
                ui.spinner(size="lg")
                ui.label("backend must be napping...").classes("text-lg mt-2")

            waiting_dialog.open()
            interval = 15  # TODO: make this configurable
            retries = 10  # TODO: make this configurable

            # TODO: remove complex retry logic as the backend is now always awake
            def attempt_login(retries_left=retries):
                print(f"Attempting login... Retries left: {retries_left}")  # Debug print
                try:
                    if retries_left == retries:
                        ui.run_javascript(
                            f"""
                            fetch("{BACKEND_URL}/docs").then(r =>
                            console.log('Backend wakeup ping sent'))
                        """
                        )
                        print("wake API called in js")  # Debug print
                    response = login_user(email.value, password.value)
                    if not response:
                        print("Login failed with given credentials")
                        ui.notify("❌ Login failed with given credentials", type="negative")
                        waiting_dialog.close()
                        return
                    else:
                        app.storage.user["token"] = response["access_token"]
                        app.storage.user["user"] = response["username"]
                        app.storage.user["id"] = response["id"]
                        waiting_dialog.close()
                        ui.notify("✅ Login successful", type="positive")
                        clear_cache()
                        ui.navigate.to(app.storage.user.get("post_login_path", "/"))
                        app.storage.user["post_login_path"] = "/"
                except Exception as e:
                    print("Exception during login:", e)  # Debug print
                    if retries_left > 0:
                        ui.timer(interval, lambda: attempt_login(retries_left - 1), once=True)
                    else:
                        waiting_dialog.close()
                        handle_backend_error()

            attempt_login()

    dialog.open()


def logout():
    app.storage.user.clear()
    ui.navigate.to("/")


def open_feedback_dialog():
    def submit_feedback(feedback_text: str):
        create_feedback(feedback_text)
        ui.notify("Thank you for your feedback!", type="positive")
        dialog.close()

    with ui.dialog() as dialog, ui.card().classes("w-full max-w-lg"):
        ui.label("We'd love your feedback!").classes("text-lg font-bold mb-2")
        feedback_text = ui.textarea(
            label="be it an idea or appreciation or a bug, " "please describe your experience!"
        ).classes("w-full")
        with ui.row().classes("justify-end gap-4 mt-4"):
            ui.button(icon="send", on_click=lambda: submit_feedback(feedback_text.value)).props("color=primary")
    dialog.open()


def open_google_login_dialog():
    # Store the current path in app.storage
    post_login_path = ui.context.client.request.url.path
    ui.navigate.to(f"/auth/google/login?post_login_path={post_login_path}")


def open_login_dialog():
    # Store the current path in app.storage
    post_login_path = ui.context.client.request.url.path
    app.storage.user["post_login_path"] = post_login_path
    login_or_signup("login")


def setup_navbar(title: str = "Ecological Journey"):
    with (
        ui.header()
        .classes("top-navbar flex items-center justify-between px-4 py-2 bg-primary fixed top-0 z-50 w-full shadow-sm")
        .style("background-color: #111827;")
    ):

        # LEFT: Title (fixed width)
        with ui.row().classes("items-center shrink-0 gap-2 w-auto"):
            with ui.link("/", target="/").classes("no-underline flex items-center"):
                ui.icon("home").classes("text-white text-2xl font-bold")
                ui.label(title).classes("text-white text-2xl font-bold ml-2")

        def nav_button(label: str, path: str):
            is_active = ui.context.client.page.path == path
            props = "flat dense"
            active = "" if not is_active else " text-black font-bold"
            return (
                ui.button(label, on_click=lambda: ui.navigate.to(path))
                .props(f"{props} color=white")
                .classes(f"normal-case px-4 py-1 text-base text-center{active}")
            )

        # CENTER: Scrollable nav links
        with ui.element("div").classes("flex-1 overflow-x-auto no-scrollbar flex justify-center"):
            with ui.button_group().classes("gap-1 items-center justify-center border-none shadow-none"):
                ui.element("div").classes("w-[40px] shrink-0")
                nav_button("Films", "/films")
                nav_button("Clips", "/clips")
                nav_button("Cliplists", "/cliplists")
                nav_button("Partners", "/partners")
                nav_button("About", "/about")
                nav_button("Notion", "/notion")

        # RIGHT: Auth buttons (fixed width, right aligned)
        with ui.row().classes("items-center shrink-0 gap-2 w-auto justify-end"):
            user = app.storage.user.get("user")
            if user:
                ui.label(f"Hi, {user}").classes("text-sm text-white")
                ui.button(icon="logout", on_click=logout).props("flat round dense color=red").tooltip("Logout")
            else:
                ui.button(icon="login", on_click=open_login_dialog).props("flat round dense color=white").tooltip(
                    "Login"
                )

    # Scroll-triggered navbar hide/show
    ui.run_javascript(
        """
        let lastScroll = 0;
        const navbar = document.querySelector('.top-navbar');
        window.addEventListener('scroll', () => {
            const current = window.scrollY;
            if (current > lastScroll && current > 60) {
                navbar.classList.add('-translate-y-full', 'opacity-0');
            } else {
                navbar.classList.remove('-translate-y-full', 'opacity-0');
            }
            lastScroll = current;
        });
    """
    )


def ecological_layout():
    setup_navbar()
    ui.run_javascript(
        """
        function showOrientationWarning() {
            if (!document.getElementById("orientation-warning")) {
                const notice = document.createElement('div');
                notice.innerHTML = `
                    <div style="
                        display: flex; flex-direction: column; align-items: center; justify-content: center;
                        width: 100vw; height: 100vh; color: #fff; text-align: center;">
                        <div style="font-size:3em; margin-bottom:0.5em;">🌿</div>
                        <div style="font-size:1.5em; font-weight:bold;">This jungle grows sideways 🌴</div>
                        <div style="font-size:1em; max-width: 90vw; margin-top: 0.5em;">
                            Please rotate your device to <b>landscape</b><br>
                            to explore the Ecological Journey. ↩️
                        </div>
                    </div>
                `;
                notice.style.position = "fixed";
                notice.style.top = "0";
                notice.style.left = "0";
                notice.style.width = "100vw";
                notice.style.height = "100vh";
                notice.style.background = "rgba(16,24,32,0.96)";
                notice.style.zIndex = "9999";
                notice.id = "orientation-warning";
                document.body.appendChild(notice);
            }
        }
        function hideOrientationWarning() {
            const existing = document.getElementById("orientation-warning");
            if (existing) existing.remove();
        }
        function checkOrientation() {
            const isPortrait = window.innerHeight > window.innerWidth;
            const isMobile = /Mobi|Android/i.test(navigator.userAgent);
            if (isMobile && isPortrait) {
                showOrientationWarning();
            } else {
                hideOrientationWarning();
            }
        }
        window.addEventListener(
            "load", checkOrientation
        );
        window.addEventListener(
            "resize", checkOrientation
        );
        window.addEventListener(
            "orientationchange", checkOrientation
        );
        checkOrientation();
    """
    )


def setup_footer():
    with ui.page_sticky(x_offset=18, y_offset=18):
        ui.button(icon="feedback", on_click=open_feedback_dialog).tooltip("Send Feedback").props(
            "round fab fixed color=secondary"
        )


@ui.page("/oauth")
def oauth_page(
    token: str = ui.query("token"),
    username: str = ui.query("username"),
    id: str = ui.query("id"),
    post_login_path: str = ui.query("post_login_path"),
):
    if token:
        app.storage.user["token"] = token
        app.storage.user["user"] = username
        app.storage.user["id"] = id
        ui.notify("✅ Google login successful", type="positive")
        clear_cache()
        ui.navigate.to(post_login_path or "/")
        app.storage.user["post_login_path"] = "/"


@ui.page("/notion")
def _():
    ecological_layout()
    notion_page()
    setup_footer()


@ui.page("/")
def _():
    ecological_layout()
    home_page()
    setup_footer()


@ui.page("/films")
def _():
    ecological_layout()
    films_page()
    setup_footer()


@ui.page("/clips")
def _():
    ecological_layout()
    clips_page()
    setup_footer()


@ui.page("/cliplists")
def _():
    ecological_layout()
    cliplists_page()
    setup_footer()


@ui.page("/partners")
def _():
    ecological_layout()
    partner_page()
    setup_footer()


@ui.page("/about")
def _():
    ecological_layout()
    about_page()
    setup_footer()


@ui.page("/playlist/{cliplist_id}")
def _(cliplist_id: str = None):
    ecological_layout()
    playlist_page(cliplist_id)
    setup_footer()


@ui.page("/film/{video_id}")
def _(video_id: str):
    ecological_layout()
    film_page(video_id)
    setup_footer()


@app.api_route("/", methods=["GET", "HEAD"], response_class=PlainTextResponse)
def root():
    return "Ecological Journey UI is alive"


# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

ui.run(
    title="Ecological Journey",
    reload=True,
    storage_secret="45d3fba306d5a694f61d0ccd684c75fa",
)

FRONTEND_URL = "http://localhost:8080"

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


@app.get("/auth/google/callback")
async def google_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        resp = await oauth.google.get("https://openidconnect.googleapis.com/v1/userinfo", token=token)
        userinfo = resp.json()
    except OAuthError:
        return RedirectResponse(url=f"{FRONTEND_URL}/?error=oauth")

    request.session["user"] = userinfo  # Or store in Redis/etc.

    # Replace with your own logic
    user = get_or_create_user(userinfo["email"], userinfo["name"], "google", userinfo["sub"])
    jwt_token = create_access_token({"sub": str(user["_id"])})

    post_login_path = request.query_params.get("state")
    return RedirectResponse(
        url=f'{FRONTEND_URL}/oauth?token={jwt_token}&username={userinfo["name"]}'
        f'&id={str(user["_id"])}&post_login_path={post_login_path}'
    )

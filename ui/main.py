import os
import sys

import requests
from dotenv import load_dotenv
from fastapi.responses import PlainTextResponse
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
from utils.utils_api import api_post as api_post_utils

sys.stdout.reconfigure(line_buffering=True)

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL")


def api_post(endpoint: str, data: dict):
    if "token" in endpoint:
        return requests.post(f"{BACKEND_URL}{endpoint}", data=data, timeout=5)
    else:
        return requests.post(f"{BACKEND_URL}{endpoint}", json=data, timeout=5)


def api_get(endpoint: str):
    token = app.storage.user.get("token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.get(f"{BACKEND_URL}{endpoint}", headers=headers, timeout=5)


def login_or_signup(mode="login"):
    with (
        ui.dialog() as dialog,
        ui.card().style("padding: 2rem; max-width: 400px; width: 90vw;").classes("w-full"),
    ):
        ui.label(f"{'Login' if mode == 'login' else 'Register'}").classes("text-xl font-bold w-full mb-6")

        with ui.column().classes("gap-4 w-full"):
            if mode != "login":
                username = ui.input("Username").classes("w-full")
            email = ui.input("Email").classes("w-full")
            password = ui.input("Password", password=True).classes("w-full")

        with ui.row().classes("justify-end gap-4 mt-6"):
            ui.button("Submit", on_click=lambda: submit()).props("color=primary")
            ui.button("Cancel", on_click=dialog.close).props("flat color=grey")

        def submit():
            endpoint = "/auth/token" if mode == "login" else "/auth/register"
            if mode == "login":
                data = {"username": email.value, "password": password.value}
            else:
                data = {"email": email.value, "password": password.value}
                data["username"] = username.value

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
                    response = api_post(endpoint, data)
                    print("API called, status:", response.status_code)  # Debug print

                    if response.status_code == 200:
                        response_data = response.json()
                        app.storage.user["token"] = response_data["access_token"]
                        app.storage.user["user"] = response_data["username"]
                        app.storage.user["id"] = response_data["id"]
                        waiting_dialog.close()
                        ui.notify("✅ Login successful", type="positive")
                        ui.navigate.to("/")  # refresh navbar

                    elif response.status_code == 503:
                        if retries_left > 0:
                            print("Backend waking up, retrying...")
                            ui.timer(
                                interval,
                                lambda: attempt_login(retries_left - 1),
                                once=True,
                            )
                        else:
                            waiting_dialog.close()
                            handle_backend_error()
                    else:
                        waiting_dialog.close()
                        ui.notify(f"❌ {response.text or 'Login failed.'}", type="negative")
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
        api_post_utils("/feedback", {"text": feedback_text}, token=app.storage.user.get("token"))
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


def setup_navbar(title: str = "Ecological Journey"):
    with (
        ui.header()
        .classes(
            "top-navbar flex items-center justify-between px-4 py-2 " "bg-primary fixed top-0 z-50 w-full shadow-sm"
        )
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
                ui.button(icon="person_add", on_click=lambda: caught_john_doe()).props(
                    "flat round dense color=white"
                ).tooltip("Register")
                ui.button(icon="login", on_click=lambda: login_or_signup("login")).props(
                    "flat round dense color=white"
                ).tooltip("Login")

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

# main.py
import os
import requests
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
from nicegui import ui, app
from about import about_page
from home_page import home_page
from films import films_page
from film import film_page
from partner import partner_page
from dialog_puns import caught_john_doe

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

def login_or_signup(mode='login'):
    with ui.dialog() as dialog, ui.card().style('padding: 2rem; max-width: 400px; width: 90vw;').classes('w-full'):
        ui.label(f"{'Login' if mode == 'login' else 'Register'}").classes('text-xl font-bold w-full mb-6')

        with ui.column().classes('gap-4 w-full'):
            if mode != 'login':
                username = ui.input("Username").classes('w-full')
            email = ui.input("Email").classes('w-full')
            password = ui.input("Password", password=True).classes('w-full')

        with ui.row().classes('justify-end gap-4 mt-6'):
            ui.button("Submit", on_click=lambda: submit()).props('color=primary')
            ui.button("Cancel", on_click=dialog.close).props('flat color=grey')

        def submit():
            endpoint = "/auth/token" if mode == 'login' else "/auth/register"
            if mode == 'login':
                data = {"username": email.value, "password": password.value}
            else:
                data = {"email": email.value, "password": password.value}
                data["username"] = username.value
            response = api_post(endpoint, data)
            if response.status_code == 200:
                data = response.json()
                app.storage.user["token"] = data["access_token"]
                app.storage.user["user"] = data["username"]
                app.storage.user["id"] = data["id"]
                ui.notify("✅ Success", type="positive")
                dialog.close()
                ui.navigate.to("/")  # reload to refresh navbar
            else:
                ui.notify(f"❌ {response.text}", type="negative")

    dialog.open()



def logout():
    app.storage.user.clear()
    ui.navigate.to("/")

def setup_navbar(title: str = '🥋 Ecological Journey'):
    current_path = ui.context.client.page.path  # Correct way to get current path

    def link(text, path):
        is_active = current_path == path
        classes = 'text-base text-white no-underline'
        if is_active:
            classes += ' font-bold border-b-2 border-white'
        return ui.link(text, path).classes(classes).style('line-height: 1.5;')  # better vertical alignment

    with ui.header().classes('flex justify-between items-center text-white px-6 py-4'):
        # Left: Title + Nav Links
        with ui.row().classes('items-center gap-8'):
            with ui.link('/', target='/').classes('no-underline flex items-center'):
                ui.label(title).classes('text-2xl font-bold text-white leading-none')  # bigger font, no extra line height
            link('Home', '/')
            link('Films', '/films')
            link('Film Study', '/film_study')
            link('Partner Study', '/partner_study')
            link('About', '/about')

        # Right: Auth Actions
        with ui.row().classes('items-center gap-4'):
            user = app.storage.user.get("user")
            if user:
                ui.label(f"Hi, {user}").classes('text-sm text-white')
                ui.button("Logout", on_click=logout).props("flat color=red").classes("text-sm")
            else:
                ui.button("Login", on_click=lambda: login_or_signup("login")).props("flat color=white").classes("text-sm")
                ui.button("Register", on_click=lambda: caught_john_doe()).props("flat color=white").classes("text-sm")

def ecological_layout():
    setup_navbar()
    ui.run_javascript('''
        function showOrientationWarning() {
            if (!document.getElementById("orientation-warning")) {
                const notice = document.createElement('div');
                notice.innerHTML = `
                    <div style="
                        display: flex; flex-direction: column; align-items: center; justify-content: center;
                        width: 100vw; height: 100vh; color: #fff; text-align: center;">
                        <span style="font-size:3em; margin-bottom:0.5em;">🥋</span>
                        <div style="font-size:2em; font-weight:bold; margin-bottom:0.5em;">
                            Landscape Mode Recommended
                        </div>
                        <div style="font-size:1.2em; max-width: 90vw;">
                            For the best Ecological Journey experience,<br>
                            please rotate your device to <b>landscape</b>.<br>
                            <span style="font-size:1.5em;">🔁</span>
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
        window.addEventListener("load", checkOrientation);
        window.addEventListener("resize", checkOrientation);
        window.addEventListener("orientationchange", checkOrientation);
    ''')

@ui.page('/')
def home():
    ecological_layout()
    home_page()

@ui.page('/film_study')
def film_study():
    ecological_layout()
    film_page("demo")

@ui.page('/films')
def films():
    ecological_layout()
    films_page()

@ui.page('/partner_study') ## TODO: think about the intention and layout again
def show_partner_page():
    ecological_layout()
    partner_page()

@ui.page('/about')
def about():
    ecological_layout()
    about_page()

@ui.page('/film/{video_id}')
def video_detail(video_id: str):
    ecological_layout()
    film_page(video_id)

@app.api_route("/", methods=["GET", "HEAD"], response_class=PlainTextResponse)
def root():
    return "Ecological Journey UI is alive"

ui.run(title='Ecological Journey', reload=True, storage_secret='45d3fba306d5a694f61d0ccd684c75fa')
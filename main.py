import os
import requests
from dotenv import load_dotenv
from nicegui import ui, app as ngapp
from ui.about import about_page
from ui.dashboard import home_page
from ui.films import films_page
from ui.film import film_page
from ui.partner import partner_page
from ui.reviewer import video_reviewer

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL")

def api_post(endpoint: str, data: dict):
    if "token" in endpoint:
        return requests.post(f"{BACKEND_URL}{endpoint}", data=data)
    else:
        return requests.post(f"{BACKEND_URL}{endpoint}", json=data)

def api_get(endpoint: str):
    token = ngapp.storage.user.get("token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.get(f"{BACKEND_URL}{endpoint}", headers=headers)

def login_or_signup(mode='login'):
    with ui.dialog() as dialog, ui.card():
        ui.label(f"{'Login' if mode == 'login' else 'Register'}").classes('text-xl font-bold')

        if mode != 'login':
            username = ui.input("Username").classes('w-full')
        email = ui.input("Email").classes('w-full')
        password = ui.input("Password", password=True).classes('w-full')

        def submit():
            endpoint = "/auth/token" if mode == 'login' else "/auth/register"
            data = {"email": email.value, "password": password.value}
            if mode != 'login': data["username"] = username.value
            response = api_post(endpoint, data)
            if response.status_code == 200:
                data = response.json()
                ngapp.storage.user["token"] = data["access_token"]
                ngapp.storage.user["user"] = data["username"]
                ui.notify("✅ Success", type="positive")
                dialog.close()
                ui.navigate.to("/")  # reload to refresh navbar
            else:
                ui.notify(f"❌ {response.text}", type="negative")

        ui.button("Submit", on_click=submit).props('color=primary')
        ui.button("Cancel", on_click=dialog.close).props('flat color=grey')

    dialog.open()

def logout():
    ngapp.storage.user.clear()
    ui.navigate.to("/")


def setup_navbar(title: str):
    with ui.header().classes('justify-between items-center text-white'):
        # Left: Title + Navigation Links
        with ui.row().classes('items-center gap-6 p-4'):
            ui.label(title).classes('text-xl')
            ui.link('Home', '/').classes('text-white no-underline')
            ui.link('Films', '/films').classes('text-white no-underline')
            ui.link('Film Study', '/film_study').classes('text-white no-underline')
            ui.link('Partner Study', '/partner_study').classes('text-white no-underline')
            ui.link('About', '/about').classes('text-white no-underline')

        # Right: Auth Actions
        with ui.row().classes('items-center gap-4 p-4'):
            user = ngapp.storage.user.get("user")
            if user:
                ui.label(f"Hi, {user}").classes('text-sm')
                ui.button("Logout", on_click=logout).props("flat color=red")
            else:
                ui.button("Login", on_click=lambda: login_or_signup("login")).props("flat color=white")
                ui.button("Register", on_click=lambda: login_or_signup("signup")).props("flat color=white")


@ui.page('/')
def home():
    setup_navbar('🥋 Ecological Journey')
    home_page()

@ui.page('/film_study') ## TODO: Make this a demo/playarea for non-users
def review():
    setup_navbar('🎞️ Film Study')
    video_reviewer()

@ui.page('/films')
def review():
    setup_navbar('🎞️ Films')
    films_page()

@ui.page('/partner_study') ## TODO: think about the intention and layout again
def show_partner_page():
    setup_navbar('📖 Partner Study')
    partner_page()

@ui.page('/about')
def about():
    setup_navbar('📖 About This Platform')
    about_page()

@ui.page('/film/{video_id}')
def video_detail(video_id: str):
    setup_navbar('📖 Film Study')
    film_page(video_id)

# ui.run(title='Ecological Journey', reload=True, storage_secret='45d3fba306d5a694f61d0ccd684c75fa')

##

# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.app.routes import router

app = FastAPI(
    title="Ecological Journey API",
    description="Video and Clip management with team-scoped access",
    security=[{"bearerAuth": []}],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

##

ui.run_with(app, title='Ecological Journey', storage_secret='45d3fba306d5a694f61d0ccd684c75fa')

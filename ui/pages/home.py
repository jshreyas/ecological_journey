import asyncio
from datetime import datetime

from dotenv import load_dotenv
from nicegui import events, ui

from ui.data.crud import AuthError, load_playlists
from ui.log import log

# from ui.pages.components.home.calendar_component import calendar_container
from ui.pages.components.home.fullcalendar import FullCalendar as fullcalendar
from ui.utils.dialog_puns import caught_john_doe
from ui.utils.user_context import User, with_user_context

# from ui.utils.utils import group_videos_by_day
from ui.utils.utils_api import (
    create_playlist,
    create_team,
    create_video,
    fetch_teams_for_user,
    load_playlists_for_user,
    load_videos,
)
from ui.utils.youtube import fetch_playlist_items, fetch_playlist_metadata

# from collections import Counter


load_dotenv()
# TODO: Refactor this file to separate concerns and reduce size.


def render_add_playlist_card(parent, user: User | None, refresh_playlists, render_dashboard):
    with parent:
        with ui.card().classes("w-full p-4 border border-gray-300 rounded-lg bg-white shadow-md gap-3"):
            ui.label("➕ Playlist by ID").classes("text-md font-bold")
            playlist_verified = {"status": False}
            playlist_id_input = ui.input("YouTube Playlist ID").classes("w-full text-sm")

            async def verify_playlist():
                playlist_id = playlist_id_input.value.strip()
                if not playlist_id:
                    ui.notify("❌ Please enter a Playlist ID.", type="warning")
                    fetch_button.disable()
                    playlist_verified["status"] = False
                    return
                metadata = await fetch_playlist_metadata(playlist_id)
                if metadata and "title" in metadata:
                    ui.notify(f'✅ Playlist verified: {metadata["title"]}', type="success")
                    fetch_button.enable()
                    playlist_verified["status"] = True
                else:
                    ui.notify("❌ Invalid Playlist ID or playlist not found.", type="error")
                    fetch_button.disable()
                    playlist_verified["status"] = False

            def on_input_change():
                fetch_button.disable()
                playlist_verified["status"] = False

            async def fetch_playlist_videos():
                if not playlist_verified["status"]:
                    ui.notify("❌ Please verify the playlist first.", type="warning")
                    return
                playlist_id = playlist_id_input.value.strip()
                metadata = await fetch_playlist_metadata(playlist_id)
                playlist_name = metadata.get("title", playlist_id)
                ui.notify(f"Fetching videos for playlist: {playlist_name}")
                spinner = ui.spinner(size="lg").props("color=primary")
                ui.timer(0.1, lambda: spinner.set_visibility(True), once=True)

                async def task():
                    playlist = create_playlist(
                        [],
                        user.token if user else None,
                        playlist_name,
                        playlist_id,
                    )
                    result = await sync_playlist(
                        playlist_obj=playlist,
                        token=user.token if user else None,
                    )
                    spinner.set_visibility(False)
                    if result == SYNC_OK:
                        ui.notify("✅ Playlist created and synced")
                    elif result == SYNC_NOOP:
                        ui.notify("ℹ️ Playlist added (no videos yet)")
                    else:
                        ui.notify("⚠️ Playlist added, sync failed")

                    refresh_playlists()
                    render_dashboard()
                    playlist_id_input.value = ""
                    fetch_button.disable()
                    playlist_verified["status"] = False

                ui.timer(0.2, task, once=True)

            playlist_id_input.on("change", on_input_change)
            with ui.row().classes("w-full justify-start gap-4"):
                ui.button(
                    on_click=(caught_john_doe if not user else verify_playlist),
                    icon="check_circle",
                ).props(
                    "flat round"
                ).tooltip("Verify Playlist")
                fetch_button = ui.button(icon="download").props("flat round").tooltip("Fetch Videos")
                fetch_button.disable()
                fetch_button.on("click", fetch_playlist_videos)


def render_video_post(video, index):
    anchor_id = get_video_anchor(video["video_id"])

    ui.element("div").props(f"id={anchor_id}")

    with ui.card().classes("w-full p-3 shadow-md"):
        with ui.link(target=f'/film/{video["video_id"]}').classes("w-full h-[50vh] p-0"):
            ui.image(f'https://img.youtube.com/vi/{video["video_id"]}/maxresdefault.jpg').classes(
                "w-full h-full rounded-md"
            )

        # 📌 Metadata
        with ui.column().classes("gap-1 mt-2"):
            with ui.row().classes("gap-2 items-center"):
                ui.label(index + 1).classes("text-sm font-bold text-gray-500")
                ui.element("div").classes(f"{video.get('playlist_color')} w-3 h-3 rounded-full")
                ui.label(f"🎵 Playlist: {video.get('playlist_name', 'N/A')}").classes("text-sm")

            partners = ", ".join(video.get("partners", []))
            if partners:
                ui.label(f"👥 {partners}").classes("text-sm text-gray-700")

            # ✂️ Clips
            clips = video.get("clips", [])
            if clips:
                with ui.row().classes("flex-wrap gap-1"):
                    for c in clips[:5]:
                        ui.chip(c.get("label", "clip")).props("dense").on(
                            "click", lambda _, c=c: ui.notify(f"Playing clip: {c.get('label', 'clip')}")
                        )


def render_date_header(date_str):
    anchor_id = get_date_anchor(date_str)

    ui.element("div").props(f"id={anchor_id}")

    with ui.row().classes("w-full max-w-3xl mx-auto px-4 mt-4 sticky top-0 bg-white z-10"):
        ui.label(format_date(date_str)).classes("text-lg font-semibold text-gray-700 border-b pb-1 w-full")


PAGE_SIZE = 50
current_index = 0
is_loading = False
last_rendered_date = None


def get_date_anchor(date_str: str):
    return f"date-{date_str.split('T')[0]}"


def get_video_anchor(video_id: str):
    return f"video-{video_id}"


def format_date(date_str):
    # assuming ISO format in DB: "2026-04-02T..."
    dt = datetime.fromisoformat(date_str)
    return dt.strftime("%A, %b %d, %Y")  # e.g. Thursday, Apr 02, 2026


def load_more(feed_container, videos):
    global current_index, is_loading, last_rendered_date

    if is_loading:
        return

    is_loading = True

    next_batch = videos[current_index : current_index + PAGE_SIZE]  # noqa: E203

    if not next_batch:
        is_loading = False
        return

    with feed_container:
        for i, v in enumerate(next_batch):
            video_date = v["date"].split("T")[0]  # normalize to YYYY-MM-DD

            # 👇 insert header when date changes
            if last_rendered_date != video_date:
                render_date_header(video_date)
                last_rendered_date = video_date

            render_video_post(v, current_index + i)

    current_index += PAGE_SIZE
    is_loading = False


def render_dashboard(parent):
    parent.clear()
    all_videos = load_videos()
    videos = sorted(all_videos, key=lambda v: v["date"], reverse=True)

    if not videos:
        with parent:
            ui.label("No videos")
        return

    global current_index, is_loading
    current_index = 0
    is_loading = False

    with parent:
        with ui.column().classes("w-full h-full overflow-auto feed-scroll"):

            feed_container = ui.column().classes("w-full max-w-3xl mx-auto gap-6 p-4")

            # initial load
            load_more(feed_container, videos)

            # 👇 sentinel (VERY IMPORTANT)
            ui.element("div").classes("feed-sentinel h-10")

    # 👇 Python event listener
    ui.on("load_more", lambda: load_more(feed_container, videos))

    # 👇 initialize scroll listener AFTER render
    ui.run_javascript(
        """
        window.scrollToAnchor = function(anchorId) {
            const container = document.querySelector('.feed-scroll');
            const el = document.getElementById(anchorId);

            if (!container || !el) return;

            const containerRect = container.getBoundingClientRect();
            const elRect = el.getBoundingClientRect();

            const offset = elRect.top - containerRect.top + container.scrollTop;

            container.scrollTo({
                top: offset - 20, // small padding
                behavior: 'smooth'
            });
        };
        (function() {
            const scrollRoot = document.querySelector('.feed-scroll');
            if (!scrollRoot) return;

            if (window.feedScrollListener && window.feedScrollRoot) {
                window.feedScrollRoot.removeEventListener('scroll', window.feedScrollListener);
            }

            window.feedScrollListener = function() {
                const root = document.querySelector('.feed-scroll');
                if (!root) return;
                const distanceFromBottom = root.scrollHeight - root.scrollTop - root.clientHeight;
                if (distanceFromBottom <= 20) {
                    const emitter =
                        typeof window.emitEvent === 'function'
                            ? window.emitEvent
                            : typeof emitEvent === 'function'
                            ? emitEvent
                            : null;
                    if (emitter) {
                        emitter('load_more');
                    }
                }
            };

            window.feedScrollRoot = scrollRoot;
            window.feedScrollRoot.addEventListener('scroll', window.feedScrollListener);

            // trigger once in case the list is shorter than the viewport
            window.feedScrollListener();
        })();
        """
    )


def render_playlists_list(parent, user: User | None, refresh_playlists, render_dashboard):
    parent.clear()

    def render_playlist_card(
        *,
        parent,
        playlist: dict,
        show_sync: bool,
        on_sync_click=None,
    ):
        with parent:
            with ui.column().classes("w-full p-2 border border-gray-300 rounded-lg bg-white shadow-md"):
                with ui.row().classes("w-full justify-between items-center"):
                    ui.label(playlist["name"]).tooltip(playlist["_id"]).classes("text-sm font-semibold")
                    # TODO: playlist owner can change the color with color picker, update the playlist backend accordingly
                    ui.element("div").classes(f"{playlist['color']} w-3 h-3 rounded-full")

                with ui.row().classes("w-full justify-between items-center"):
                    ui.label(f"🎬 {playlist.get('video_count')}").classes("text-xs text-gray-600")

                    if show_sync and on_sync_click:
                        ui.button(
                            icon="sync",
                            on_click=on_sync_click,
                        ).props(
                            "flat dense round color=primary"
                        ).tooltip("Sync")

    # ---------- Guest (no user) ----------
    if not user:
        for playlist in load_playlists():
            render_playlist_card(
                parent=parent,
                playlist=playlist,
                show_sync=True,
                on_sync_click=lambda: caught_john_doe(),
            )

    # ---------- Authenticated user ----------
    else:
        both = load_playlists_for_user(user.id)
        owned, member = both["owned"], both["member"]
        owned_ids = {pl["_id"] for pl in owned}
        all_playlists = owned + [p for p in member if p["_id"] not in owned_ids]

        def on_user_sync_click(parent, playlist_obj: dict, token: str):
            playlist_id = playlist_obj["_id"]
            playlist_name = playlist_obj["name"]

            async def run():
                try:
                    log.info(f"User-initiated sync for playlist: {playlist_name} ({playlist_id})")
                    result = await sync_playlist(
                        playlist_obj=playlist_obj,
                        token=token,
                    )

                    with parent:
                        if result == SYNC_OK:
                            ui.notify("Playlist synced successfully", type="positive")
                        elif result == SYNC_NOOP:
                            ui.notify("No new videos to sync", type="info")
                        elif result == SYNC_RETRY_SOON:
                            ui.notify("Upload still in progress — try again shortly", type="warning")
                        else:
                            ui.notify("Sync failed", type="negative")

                except Exception as e:
                    with parent:
                        ui.notify(f"Sync failed: {e}", type="negative")

            log.info(f"Preparing to sync playlist: {playlist_name} ({playlist_id})")
            return run

        def on_sync_click(parent, playlist_obj, token):
            spinner = ui.spinner(size="lg").props("color=primary")
            spinner.set_visibility(True)

            async def do_sync():
                try:
                    await on_user_sync_click(parent, playlist_obj, token)()
                except Exception as e:
                    ui.notify(f"❌ Sync failed: {str(e)}")
                finally:
                    spinner.set_visibility(False)
                    refresh_playlists()
                    render_dashboard()

            ui.timer(0.1, lambda: asyncio.create_task(do_sync()), once=True)

        for playlist in all_playlists:
            is_owned = playlist["_id"] in owned_ids

            render_playlist_card(
                parent=parent,
                playlist=playlist,
                show_sync=is_owned,
                on_sync_click=(lambda p=playlist: on_sync_click(parent, p, user.token) if is_owned else None),
            )

    render_add_playlist_card(parent, user, refresh_playlists, render_dashboard)


TAILWIND_TO_HEX = {
    "bg-red-400": "#f87171",
    "bg-blue-400": "#60a5fa",
    "bg-green-400": "#4ade80",
    "bg-yellow-400": "#facc15",
    "bg-purple-400": "#c084fc",
    "bg-pink-400": "#f472b6",
    "bg-indigo-400": "#818cf8",
    "bg-gray-400": "#9ca3af",
}


def get_event_color(tw_class: str | None):
    if not tw_class:
        return "#888888"
    return TAILWIND_TO_HEX.get(tw_class, "#888888")


def build_calendar_events(videos: list[dict]) -> list[dict]:
    events = []

    for v in videos:
        start = v["date"].split("T")[0]

        events.append(
            {
                "id": v["video_id"],  # 👈 CRITICAL for navigation
                "title": "",  # v.get("playlist_name", "Video"),
                "start": start,
                "allDay": False,
                "backgroundColor": get_event_color(v.get("playlist_color")),
                "borderColor": get_event_color(v.get("playlist_color")),
            }
        )

    return events


@with_user_context
def home_page(user: User | None):
    with ui.splitter(value=50).classes("w-full h-[600px] gap-4") as splitter:
        with splitter.before:
            with ui.tabs().classes("w-full") as tabs:
                tab_playlists = ui.tab("🎵 Playlists")
                tab_teams = ui.tab("👥 Teams")
                # tab_calendar = ui.tab("📅 Calendar")
                tab_newc = ui.tab("📅 Calendar")
            with ui.tab_panels(tabs, value=tab_newc).classes("w-full h-full"):
                with ui.tab_panel(tab_playlists) as playlists_container:

                    def refresh_playlists():
                        render_playlists_list(
                            playlists_container,
                            user,
                            refresh_playlists,
                            lambda: render_dashboard(dashboard_column),
                        )

                    refresh_playlists()
                with ui.tab_panel(tab_teams) as teams_container:

                    def refresh_teams():
                        teams_container.clear()
                        if not user:
                            both = fetch_teams_for_user_jd(44)
                        else:
                            both = fetch_teams_for_user(user.id)
                        owned, member = both["owned"], both["member"]
                        owned_ids = {t["_id"] for t in owned}
                        all_teams = owned + [t for t in member if t["_id"] not in owned_ids]
                        with ui.column().classes(
                            "w-full p-4 border border-gray-300 rounded-lg bg-white shadow-md gap-3"
                        ):
                            with ui.row().classes("w-full justify-between items-center"):

                                def create_new_team():
                                    name = team_name_input.value.strip()
                                    if not name:
                                        ui.notify("Please enter a team name.", type="warning")
                                        return
                                    create_team(name, user.token, user.id)
                                    ui.notify(f'Team "{name}" created successfully!')
                                    refresh_teams()
                                    team_name_input.value = ""

                                ui.label("➕ Team").classes("text-sd font-bold")
                                ui.button(
                                    on_click=(caught_john_doe if not user else create_new_team),
                                    icon="save",
                                ).props("flat round").tooltip("Create Team")
                            team_name_input = ui.input("Team Name").classes("w-full")
                        for team in all_teams:
                            with teams_container:
                                with ui.column().classes(
                                    "w-full p-4 border border-gray-300 rounded-lg bg-white shadow-md"
                                ):
                                    with ui.row().classes("w-full justify-between items-center"):
                                        ui.label(team["name"]).classes("text-lg font-bold")
                                        if team["_id"] in owned_ids:
                                            with ui.row().classes("w-full"):
                                                ui.button(
                                                    icon="person_add",
                                                    on_click=lambda t=team: open_add_user_modal(t),
                                                ).props("flat round").tooltip("Add User")
                                                ui.button(
                                                    icon="playlist_add",
                                                    on_click=lambda t=team: open_add_playlist_modal(t),
                                                ).props("flat round").tooltip("Add Playlist")
                                                ui.button(
                                                    icon="manage_accounts",
                                                    on_click=lambda t=team: open_team_modal(t),
                                                ).props("flat round").tooltip("Manage Team")
                                    with ui.row().classes("w-full justify-between items-center"):
                                        ui.label(f"👥 {len(team.get('member_ids', []))}").classes(
                                            "text-sm text-gray-600"
                                        )
                                        ui.label(f"🎵 {team.get('playlist_count', 0)}").classes("text-sm text-gray-600")

                    refresh_teams()
                # with ui.tab_panel(tab_calendar).classes("w-full h-full p-0"):
                #     calendar_container(group_videos_by_day(load_videos()))
                with ui.tab_panel(tab_newc).classes("w-full h-full p-0"):
                    eves = build_calendar_events(load_videos())
                    options = {
                        "initialView": "dayGridMonth",
                        "headerToolbar": {"left": "prev", "center": "title", "right": "next"},
                        "allDaySlot": False,
                        "timeZone": "local",
                        "height": "auto",
                        "width": "auto",
                        "events": eves,
                    }

                    def handle_click(event: events.GenericEventArguments):
                        if "info" not in event.args:
                            return

                        event_data = event.args["info"]["event"]

                        # 👇 choose navigation strategy
                        video_id = event_data.get("id")
                        date_str = event_data.get("start", "").split("T")[0]

                        if video_id:
                            anchor = get_video_anchor(video_id)
                        else:
                            anchor = get_date_anchor(date_str)

                        ui.run_javascript(f"scrollToAnchor('{anchor}')")

                    fullcalendar(options, on_click=handle_click)

        with splitter.after:
            with ui.column().classes("w-full h-full") as dashboard_column:

                def render_dashboard_wrapper():
                    render_dashboard(dashboard_column)

                render_dashboard_wrapper()


# --- Stubbed Actions ---
def fetch_teams_for_user_jd(user_id):
    # Sample data to simulate backend result
    return {
        "owned": [
            {
                "_id": "team1",
                "name": "Mat Lab",
                "owner_id": user_id,
                "playlist_count": 2,
                "member_ids": ["user2", "user3", "user3"],
            }
        ],
        "member": [
            {
                "_id": "team2",
                "name": "Mao Pelo Pe",
                "playlist_count": 5,
                "owner_id": "another_user",
                "member_ids": [
                    user_id,
                    "user4",
                    "user22",
                    "user31",
                    "user2",
                    "user3",
                    "user4",
                ],
            }
        ],
    }


def open_add_user_modal(team):
    with ui.dialog() as dialog, ui.card().classes("w-[30rem]"):
        ui.label(f'➕ Add user to {team["name"]}').classes("text-lg font-semibold")

        # Stubbed user list (replace with real API call later)
        all_users = [
            {"email": "alice@example.com", "name": "Alice"},
            {"email": "bob@example.com", "name": "Bob"},
            {"email": "charlie@example.com", "name": "Charlie"},
        ]

        # Map email -> display name (email)
        user_map = {u["email"]: f'{u["name"]} ({u["email"]})' for u in all_users}

        user_select = ui.select(user_map, label="Select User")

        def add_user():
            email = user_select.value
            if not email:
                ui.notify("⚠️ Please select a user.", type="warning")
                return
            log.info(f"Adding user {email} to team {team['_id']}")
            ui.notify(f"✅ Added {email} to {team['name']}")
            dialog.close()

        with ui.row().classes("gap-2 mt-3"):
            ui.button("Add User", on_click=add_user).props("color=primary")
            ui.button("Cancel", on_click=dialog.close).props("flat")

    dialog.open()


def open_add_playlist_modal(team):
    with ui.dialog() as dialog, ui.card().classes("w-[30rem]"):
        ui.label(f'🎵 Add playlist to {team["name"]}').classes("text-lg font-semibold")

        # Stubbed playlist list (replace with call to load_playlists_for_user)
        user_playlists = [
            {"_id": "pl1", "name": "Top Transitions"},
            {"_id": "pl2", "name": "Submission Chains"},
        ]

        playlist_select = ui.select([pl["name"] for pl in user_playlists], label="Select Playlist")

        def add_playlist():
            selected_name = playlist_select.value
            if not selected_name:
                ui.notify("⚠️ Please select a playlist.", type="warning")
                return
            selected = next(pl for pl in user_playlists if pl["name"] == selected_name)
            log.info(f"Assigning playlist '{selected['_id']}' to team '{team['_id']}'")
            ui.notify(f"✅ Added '{selected_name}' to team {team['name']}")
            dialog.close()

        with ui.row().classes("gap-2 mt-3"):
            ui.button("Add Playlist", on_click=add_playlist).props("color=primary")
            ui.button("Cancel", on_click=dialog.close).props("flat")

    dialog.open()


def open_team_modal(team):
    with ui.dialog() as dialog, ui.card().classes("w-[40rem]"):
        ui.label(f"👥 Team: {team['name']}").classes("text-lg font-semibold")

        members = [
            {
                "name": "Alice",
                "email": "alice@example.com",
                "role": "member",
                "joined": "2024-01-10",
            },
            {
                "name": "Bob",
                "email": "bob@example.com",
                "role": "member",
                "joined": "2024-02-12",
            },
        ]

        member_container = ui.column().classes("gap-2 mt-2")

        def refresh():
            member_container.clear()
            for member in members:
                with member_container:
                    with ui.row().classes("items-center justify-between w-full"):
                        ui.label(
                            f"{member['name']} ({member['email']}) - \
                            {member['role']}, joined: {member['joined']}"
                        )
                        ui.button("Remove", on_click=lambda m=member: remove_member(m)).props("flat dense").classes(
                            "text-red-500"
                        )

        def remove_member(member):
            members.remove(member)
            ui.notify(f'Removed {member["name"]}')
            refresh()

        refresh()

        ui.button("Close", on_click=dialog.close).classes("mt-4")

    dialog.open()


SYNC_OK = "ok"
SYNC_NOOP = "noop"
SYNC_RETRY_SOON = "retry_soon"
SYNC_ERROR = "error"


async def sync_playlist(
    playlist_obj: dict,
    token: str,
) -> str:
    playlist_name = playlist_obj["name"]
    try:
        existing_videos = load_videos(playlist_obj["_id"])

        if existing_videos:
            latest_saved_date = max(video["date"] for video in existing_videos)
            existing_video_ids = [video["video_id"] for video in existing_videos]
        else:
            latest_saved_date = None
            existing_video_ids = set()

        playlist_obj["latest_saved_date"] = latest_saved_date
        playlist_obj["existing_video_ids"] = existing_video_ids
        new_video_data_dict = await fetch_playlist_items([playlist_obj])
        new_video_data = new_video_data_dict[playlist_obj["_id"]]
        if not new_video_data:
            log.info(f"[{playlist_name}] No new videos")
            return SYNC_NOOP

        create_video(new_video_data, token, playlist_obj["_id"])
        log.info(f"[{playlist_name}] Synced {len(new_video_data)} videos")
        return SYNC_OK

    except AuthError as e:
        log.error(f"[{playlist_name}] Auth error: {e}")
        return SYNC_ERROR

    except Exception as e:
        msg = str(e)
        log.info(f"[{playlist_name}] {msg}")

        # 👇 detect active-upload validation error
        if "duration_seconds" in msg and "Field required" in msg:
            log.warning(f"[{playlist_name}] Upload in progress detected, retrying soon")
            return SYNC_RETRY_SOON

        log.exception(f"[{playlist_name}] Sync failed")
        return SYNC_ERROR


def create_team_modal():
    log.info("Opening modal to create a new team")


def view_playlist_videos(playlist):
    log.info(f"Viewing videos for playlist: {playlist['title']}")

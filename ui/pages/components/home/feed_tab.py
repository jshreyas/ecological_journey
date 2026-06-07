from nicegui import ui

from ui.utils.utils import format_date
from ui.utils.video_player import VideoPlayer

from .state import State

PAGE_SIZE = 50


class FeedTab:
    """Component for displaying feed"""

    def __init__(self, home_state: State):
        self.home_state = home_state
        self.container = None
        self.current_index = 0
        self.is_loading = False
        self.last_rendered_date = None

        # inline player state
        self.active_video_id = None

        # {
        #   video_id: {
        #       "container": ui.column,
        #       "video": video_dict,
        #   }
        # }
        self.video_post_refs = {}

        self.home_state.add_refresh_callback(self.refresh)

    def create_tab(self, container):
        self.container = container
        self.refresh()

    def refresh(self):
        if not self.container:
            return

        self.current_index = 0
        self.is_loading = False
        self.last_rendered_date = None

        self.active_video_id = None
        self.video_post_refs.clear()

        self.container.clear()

        with self.container:
            self._create_feed_ui()

    def render_video_post(self, video, index):
        anchor_id = self.home_state.get_video_anchor(video["video_id"])

        ui.element("div").props(f"id={anchor_id}")

        with ui.card().classes("w-full p-3 shadow-md"):

            media_container = ui.column().classes("w-full h-[50vh]")

            self.video_post_refs[video["video_id"]] = {
                "container": media_container,
                "video": video,
            }

            self.render_thumbnail(video, media_container)

            # metadata
            with ui.column().classes("gap-1 mt-2"):

                with ui.row().classes("w-full items-center px-2"):
                    with (
                        ui.grid(columns=5)
                        .classes("w-full items-center text-sm")
                        .style("grid-template-columns: auto auto 80px 80px;")
                    ):

                        with ui.row().classes("items-center gap-2"):
                            with ui.element("div").classes(
                                f"bg-[{video.get('playlist_color')}] "
                                "w-6 h-6 rounded-full flex items-center justify-center"
                            ):
                                ui.label("🎵").classes("text-left")

                            ui.label(f"{video.get('playlist_name')}").classes("text-left")

                        ui.label(f"⏱️ {video.get('duration_human', '--:--')}").classes("text-left")

                        ui.label(f"🎬 {len(video.get('clips', []))}").classes("text-right")

                        ui.label(f"⚓ {len(video.get('anchors', []))}").classes("text-right")

                partners = ", ".join(video.get("partners", []))
                if partners:
                    ui.label(f"👥 {partners}").classes("w-full items-center px-2 text-sm text-gray-700")

    def restore_thumbnail(self, video_id: str):
        ref = self.video_post_refs.get(video_id)

        if not ref:
            return

        container = ref["container"]
        video = ref["video"]

        container.clear()

        self.render_thumbnail(video, container)

    def stop_video(self, video_id: str):

        if self.active_video_id == video_id:
            self.active_video_id = None

        self.restore_thumbnail(video_id)

    def play_video_inline(self, video):

        video_id = video["video_id"]

        # already playing
        if self.active_video_id == video_id:
            return

        # stop old player
        if self.active_video_id and self.active_video_id in self.video_post_refs:
            self.restore_thumbnail(self.active_video_id)

        self.active_video_id = video_id

        ref = self.video_post_refs.get(video_id)

        if not ref:
            return

        container = ref["container"]

        container.clear()

        self.render_player(video, container)

    def render_thumbnail(self, video, container):

        with container:

            ui.image(f"https://img.youtube.com/vi/{video['video_id']}/maxresdefault.jpg").classes(
                "w-full h-full rounded-md cursor-pointer"
            ).on(
                "click",
                lambda _: self.play_video_inline(video),
            )

    def render_date_header(self, date_str):
        anchor_id = self.home_state.get_date_anchor(date_str)

        ui.element("div").props(f"id={anchor_id}")

        with ui.row().classes("w-full mx-auto px-4 mt-4 sticky top-0 bg-white z-10"):
            ui.label(format_date(date_str)).classes("text-lg font-semibold text-gray-700 border-b pb-1 w-full")

    def load_more(self, videos):

        if self.is_loading:
            return

        self.is_loading = True

        next_batch = videos[self.current_index : self.current_index + PAGE_SIZE]  # noqa: E203

        if not next_batch:
            self.is_loading = False
            return

        with self.feed_container:
            for i, v in enumerate(next_batch):

                video_date = v["date"].split("T")[0]

                if self.last_rendered_date != video_date:
                    self.render_date_header(video_date)
                    self.last_rendered_date = video_date

                self.render_video_post(
                    v,
                    self.current_index + i,
                )

        self.current_index += PAGE_SIZE
        self.is_loading = False

    def _create_feed_ui(self):
        """Create the feed UI"""

        videos = sorted(self.home_state.load_videos(), key=lambda v: v["date"], reverse=True)

        if not videos:
            ui.label("No videos")
            return

        with ui.column().classes("w-full h-full overflow-auto feed-scroll"):

            self.feed_container = ui.column().classes("w-full mx-auto gap-6 p-4")

            # initial load
            self.load_more(videos)

            # 👇 sentinel (VERY IMPORTANT)
            ui.element("div").classes("feed-sentinel h-10")

        # 👇 Python event listener
        ui.on(
            "load_more",
            lambda: self.load_more(sorted(self.home_state.load_videos(), key=lambda v: v["date"], reverse=True)),
        )

        # 👇 initialize scroll listener AFTER render
        ui.run_javascript(
            """
            window.scrollToAnchor = async function(anchorId) {
                const container = document.querySelector('.feed-scroll');
                if (!container) return;

                for (let i = 0; i < 25; i++) {  // 👈 retry limit (prevents infinite loop)
                    const el = document.getElementById(anchorId);

                    if (el) {
                        const containerRect = container.getBoundingClientRect();
                        const elRect = el.getBoundingClientRect();

                        const offset = elRect.top - containerRect.top + container.scrollTop;

                        container.scrollTo({
                            top: offset - 20,
                            behavior: 'smooth'
                        });

                        return;
                    }

                    // 👇 trigger backend load_more
                    const emitter =
                        typeof window.emitEvent === 'function'
                            ? window.emitEvent
                            : typeof emitEvent === 'function'
                            ? emitEvent
                            : null;

                    if (emitter) {
                        emitter('load_more');
                    }

                    // 👇 wait for DOM to update
                    await new Promise(resolve => setTimeout(resolve, 200));
                }

                console.warn("Anchor not found after loading attempts:", anchorId);
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

    def render_player(self, video, container):

        # IMPORTANT:
        # VideoPlayer already renders inside parent=container
        VideoPlayer(
            video["video_id"],
            show_speed_slider=False,
            parent=container,
        )

        with container:
            with ui.row().classes("w-full justify-end"):
                ui.button(
                    icon="edit",
                    on_click=lambda: ui.navigate.to(f"/film/{video['video_id']}"),
                )
                ui.button(
                    icon="close",
                    on_click=lambda: self.stop_video(video["video_id"]),
                )

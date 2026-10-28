import json
from urllib.parse import parse_qs, urlparse

from nicegui import app, ui

from ui.utils.utils import format_time


class VideoPlayer:

    def __init__(
        self,
        video_url: str,
        start: int = 0,
        end: int = 1000000,
        speed: float = 1.0,
        show_speed_slider: bool = True,
        width: int = 700,
        height: int = 400,
        on_end=None,
        parent=None,
        video_state=None,
        playback_key: str | None = None,
    ):
        self.video_id = self._extract_video_id(video_url)
        self.start = start
        self.end = end
        self.speed = speed
        self.show_speed_slider = show_speed_slider
        self.width = width
        self.height = height
        self.on_end = on_end
        self.parent = parent
        self.video_state = video_state
        self.playback_key = playback_key
        self._render()

    def _extract_video_id(self, url: str) -> str:
        if "youtube.com" in url:
            parsed_url = urlparse(url)
            query = parse_qs(parsed_url.query)
            return query.get("v", [""])[0]
        elif "youtu.be" in url:
            return url.split("/")[-1]
        else:
            return url  # assume it's already a video ID

    def _render(self):
        import uuid

        self.element_id = f"yt-player-{uuid.uuid4().hex[:8]}"
        playback_key_json = json.dumps(self.playback_key)

        # 👇 Everything below happens in the right container
        context = self.parent if self.parent else ui
        with context:

            ui.html(
                f"""
                <div id="yt-player-wrapper" style="top: 0; left: 0; width: 100%; height: 100%; padding-bottom: 56.25%; overflow: hidden;">
                    <div id="{self.element_id}" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; overflow: hidden;"></div>
                </div>
            """
            )

            if self.on_end:
                endpoint = f"/_nicegui_api/{self.element_id}_on_end"

                @app.post(endpoint)
                async def _on_end_event():
                    if callable(self.on_end):
                        self.on_end()
                    return {"status": "ok"}

            js_on_end = (
                f"""
                fetch('/_nicegui_api/{self.element_id}_on_end', {{method: 'POST'}});
                """
                if self.on_end
                else ""
            )

            ui.run_javascript(
                f"""
                window.ytConfig = {{
                    videoId: "{self.video_id}",
                    start: {self.start},
                    end: {self.end},
                    speed: {self.speed}
                }};

                const theaterPlaybackKey = {playback_key_json};
                window.theaterPlaybackPositions = window.theaterPlaybackPositions || {{}};
                window.clearTheaterPlaybackPosition = function(key) {{
                    if (window.theaterPlaybackKey !== key) return;
                    if (window.theaterPlaybackCleanup) window.theaterPlaybackCleanup();
                    delete window.theaterPlaybackPositions[key];
                    delete window.theaterPlaybackKey;
                    delete window.theaterPlaybackCleanup;
                    window.ytPlayer = null;
                }};

                if (window.theaterPlaybackCleanup) {{
                    const previousKey = window.theaterPlaybackKey;
                    window.theaterPlaybackCleanup();
                    if (previousKey) delete window.theaterPlaybackPositions[previousKey];
                    delete window.theaterPlaybackKey;
                    delete window.theaterPlaybackCleanup;
                }}

                let ytPlayer;
                let ytEndInterval;
                let fullscreenHandler;
                let playbackDisposed = false;

                if (theaterPlaybackKey) {{
                    window.theaterPlaybackKey = theaterPlaybackKey;
                    window.theaterPlaybackCleanup = function() {{
                        playbackDisposed = true;
                        if (ytEndInterval) clearInterval(ytEndInterval);
                        if (fullscreenHandler) {{
                            document.removeEventListener('fullscreenchange', fullscreenHandler);
                        }}
                        if (ytPlayer && typeof ytPlayer.destroy === 'function') {{
                            ytPlayer.destroy();
                        }}
                    }};
                }}

                window.onYouTubeIframeAPIReady = function() {{
                    ytPlayer = new YT.Player('{self.element_id}', {{
                        height: '100%',
                        width: '100%',
                        videoId: window.ytConfig.videoId,
                        playerVars: {{
                            autoplay: 1,
                            start: window.ytConfig.start
                        }},
                        events: {{
                            'onReady': onPlayerReady,
                            'onStateChange': onPlayerStateChange
                        }}
                    }});
                }};

                function onPlayerReady(event) {{
                    if (playbackDisposed) {{
                        event.target.destroy();
                        return;
                    }}

                    const savedPosition = theaterPlaybackKey
                        ? window.theaterPlaybackPositions[theaterPlaybackKey]
                        : null;
                    if (Number.isFinite(savedPosition) && savedPosition > window.ytConfig.start) {{
                        event.target.seekTo(savedPosition, true);
                    }}
                    event.target.setPlaybackRate(window.ytConfig.speed);
                    event.target.playVideo();

                    // Set global ytPlayer reference
                    window.ytPlayer = event.target;

                    // Define helper after player is ready
                    window.getYTCurrentTime = function() {{
                        if (window.ytPlayer && typeof window.ytPlayer.getCurrentTime === "function") {{
                            return window.ytPlayer.getCurrentTime();
                        }}
                        return null;
                    }};

                    window.seekYTPlayer = function(seconds) {{
                        if (
                            window.ytPlayer &&
                            typeof window.ytPlayer.seekTo === 'function'
                        ) {{
                            window.ytPlayer.seekTo(seconds, true);
                            if (
                                typeof window.ytPlayer.playVideo === 'function'
                            ) {{
                                window.ytPlayer.playVideo();
                            }}
                        }}
                    }};

                    if (ytEndInterval) clearInterval(ytEndInterval);
                    ytEndInterval = setInterval(() => {{
                        const current = ytPlayer.getCurrentTime();
                        if (theaterPlaybackKey && Number.isFinite(current)) {{
                            window.theaterPlaybackPositions[theaterPlaybackKey] = current;
                        }}
                        if (current >= window.ytConfig.end) {{
                            ytPlayer.pauseVideo();
                            clearInterval(ytEndInterval);
                            if (theaterPlaybackKey) {{
                                delete window.theaterPlaybackPositions[theaterPlaybackKey];
                            }}
                            {js_on_end}
                        }}
                    }}, 500);

                    if (theaterPlaybackKey) {{
                        let wasFullscreen = false;
                        fullscreenHandler = function() {{
                            const isFullscreen = document.fullscreenElement === event.target.getIframe();
                            if (isFullscreen) {{
                                const current = event.target.getCurrentTime();
                                if (Number.isFinite(current)) {{
                                    window.theaterPlaybackPositions[theaterPlaybackKey] = current;
                                }}
                            }} else if (wasFullscreen) {{
                                const current = event.target.getCurrentTime();
                                const saved = window.theaterPlaybackPositions[theaterPlaybackKey];
                                const resumeAt = current > 1 || !Number.isFinite(saved) ? current : saved;
                                window.setTimeout(() => {{
                                    if (playbackDisposed || !window.ytPlayer || !Number.isFinite(resumeAt)) return;
                                    const currentPosition = window.ytPlayer.getCurrentTime();
                                    if (resumeAt > currentPosition + 1) {{
                                        window.ytPlayer.seekTo(resumeAt, true);
                                        window.ytPlayer.playVideo();
                                    }}
                                }}, 300);
                            }}
                            wasFullscreen = isFullscreen;
                        }};
                        document.addEventListener('fullscreenchange', fullscreenHandler);
                    }}
                }}

                function onPlayerStateChange(event) {{}}

                window.setYTClip = function(start, end) {{
                    window.ytConfig.start = start;
                    window.ytConfig.end = end;
                    ytPlayer.seekTo(start, true);
                    ytPlayer.playVideo();
                    if (ytEndInterval) clearInterval(ytEndInterval);
                    ytEndInterval = setInterval(() => {{
                        const current = ytPlayer.getCurrentTime();
                        if (current >= window.ytConfig.end) {{
                            ytPlayer.pauseVideo();
                            clearInterval(ytEndInterval);
                            {js_on_end}
                        }}
                    }}, 500);
                }};

                window.setYTSpeed = function(speed) {{
                    window.ytConfig.speed = speed;
                    if (ytPlayer && ytPlayer.setPlaybackRate) {{
                        ytPlayer.setPlaybackRate(speed);
                    }}
                }};

                (async function() {{

                    let attempts = 0;

                    while (
                        (!window.YT || !window.YT.Player)
                        && attempts < 100
                    ) {{
                        await new Promise(resolve => setTimeout(resolve, 100));
                        attempts++;
                    }}

                    if (window.YT && window.YT.Player) {{
                        window.onYouTubeIframeAPIReady();
                    }} else {{
                        console.error(
                            "YouTube iframe API failed to load"
                        );
                    }}

                }})();
            """
            )

            if self.show_speed_slider:

                def on_speed_change(_):
                    self.speed = speed_knob.value
                    ui.run_javascript(f"window.setYTSpeed({speed_knob.value});")

                with ui.row().classes("items-center justify-center"):
                    speed_knob = (
                        ui.knob(
                            min=0.25,
                            max=2.0,
                            step=0.25,
                            value=self.speed,
                            track_color="grey-2",
                            show_value=True,
                        )
                        .props("size=60")
                        .on("change", on_speed_change)
                    )
            # TODO: is this logic appropriate in VideoPlayer?
            if self.video_state:

                async def _add_anchor():
                    t = await ui.run_javascript("window.getYTCurrentTime();")
                    if t is not None:
                        ui.notify(
                            f"Adding anchor at time: {format_time(int(t))}",
                            type="info",
                            position="bottom",
                            timeout=2000,
                        )
                        self.video_state.add_anchor_at_time(t)
                        self.video_state.tabber.set_value("Control Panel")

                ui.button(icon="bookmark_add", on_click=_add_anchor)

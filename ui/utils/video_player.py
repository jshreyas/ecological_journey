from urllib.parse import parse_qs, urlparse

from nicegui import app, ui


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
        tick_ms: int = 100,  # how often the fake-speed loop ticks (ms); lower = smoother but more CPU
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
        self.tick_ms = tick_ms
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

        context = self.parent if self.parent else ui
        with context:

            ui.html(
                f"""
                <div id="yt-player-wrapper" style="top: 0; left: 0; width: 100%; height: 100%; padding-bottom: 56.25%; overflow: hidden;">
                    <div id="{self.element_id}" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; overflow: hidden;"></div>
                </div>
            """
            )

            ui.add_head_html(
                """
                <script src="https://www.youtube.com/iframe_api"></script>
            """
            )

            if self.on_end:
                endpoint = f"/_nicegui_api/{self.element_id}_on_end"

                @app.post(endpoint)
                async def _on_end_event():
                    if callable(self.on_end):
                        self.on_end()
                    return {"status": "ok"}

            js_on_end = f"fetch('/_nicegui_api/{self.element_id}_on_end', {{method: 'POST'}});" if self.on_end else ""

            ui.run_javascript(
                f"""
                window.ytConfig = {{
                    videoId: "{self.video_id}",
                    start: {self.start},
                    end: {self.end},
                    speed: {self.speed},
                    tick: {self.tick_ms}
                }};

                let ytPlayer;
                let ytEndInterval = null;
                let fakeSpeedInterval = null;
                let isFakeSpeed = false;

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

                function handleEnd() {{
                    try {{
                        if (ytEndInterval) {{ clearInterval(ytEndInterval); ytEndInterval = null; }}
                        if (fakeSpeedInterval) {{ clearInterval(fakeSpeedInterval); fakeSpeedInterval = null; }}
                        isFakeSpeed = false;
                        if (ytPlayer && ytPlayer.pauseVideo) {{ ytPlayer.pauseVideo(); }}
                        if (ytPlayer && ytPlayer.seekTo) {{ ytPlayer.seekTo(window.ytConfig.end, true); }}
                        {js_on_end}
                    }} catch (e) {{
                        console.warn('handleEnd error', e);
                    }}
                }}

                function startEndMonitor() {{
                    try {{
                        if (ytEndInterval) {{ clearInterval(ytEndInterval); }}
                        // check end reasonably frequently (bounded by tick); don't go too small to avoid perf hits
                        const endCheckTick = Math.max(100, Math.floor(window.ytConfig.tick));
                        ytEndInterval = setInterval(() => {{
                            try {{
                                if (!(ytPlayer && ytPlayer.getCurrentTime)) return;
                                const current = ytPlayer.getCurrentTime();
                                if (current >= window.ytConfig.end) {{
                                    handleEnd();
                                }}
                            }} catch (e) {{
                                // swallow
                            }}
                        }}, endCheckTick);
                    }} catch (e) {{
                        console.warn('startEndMonitor error', e);
                    }}
                }}

                function onPlayerReady(event) {{
                    // ensure monitoring is active
                    startEndMonitor();
                    // ensure initial speed applied
                    window.setYTSpeed(window.ytConfig.speed);
                    // start playing
                    try {{ event.target.playVideo(); }} catch(e) {{ /* ignore */ }}
                }}

                function onPlayerStateChange(event) {{
                    // fakeSpeedInterval checks player state before seeking,
                    // but keep end monitor running so end always honoured.
                }}

                window.setYTClip = function(start, end) {{
                    window.ytConfig.start = start;
                    window.ytConfig.end = end;
                    if (ytPlayer && ytPlayer.seekTo) {{
                        try {{ ytPlayer.seekTo(start, true); }} catch(e) {{ /* ignore */ }}
                    }}
                    startEndMonitor();
                }};

                window.setYTSpeed = function(speed) {{
                    window.ytConfig.speed = speed;

                    // clear any old fake interval
                    if (fakeSpeedInterval) {{ clearInterval(fakeSpeedInterval); fakeSpeedInterval = null; }}
                    isFakeSpeed = false;

                    // apply native playback rate where possible (caps at 2x)
                    if (ytPlayer && ytPlayer.setPlaybackRate) {{
                        try {{
                            if (speed <= 2.0) {{
                                ytPlayer.setPlaybackRate(speed);
                            }} else {{
                                // keep native at 2x to reduce audio/visual mismatch
                                ytPlayer.setPlaybackRate(2.0);
                            }}
                        }} catch (e) {{
                            // ignore if player not ready
                        }}
                    }}

                    if (speed > 2.0) {{
                        // start fake speed simulation (only advances while actual player state is PLAYING)
                        isFakeSpeed = true;
                        const tick = Math.max(50, Math.floor(window.ytConfig.tick)); // don't go below 50ms
                        fakeSpeedInterval = setInterval(() => {{
                            try {{
                                if (!(ytPlayer && ytPlayer.getCurrentTime && ytPlayer.getPlayerState)) return;
                                const state = ytPlayer.getPlayerState();
                                // YT.PlayerState.PLAYING === 1; be robust if YT.PlayerState is unavailable
                                if (typeof YT !== 'undefined' && YT && typeof YT.PlayerState !== 'undefined') {{
                                    if (state !== YT.PlayerState.PLAYING) return;
                                }} else {{
                                    if (state !== 1) return;
                                }}

                                const cur = ytPlayer.getCurrentTime();
                                const increment = speed * (tick / 1000); // seconds to jump per tick
                                const next = cur + increment;

                                // if next is beyond clip end, fire handleEnd immediately
                                if (next >= window.ytConfig.end) {{
                                    handleEnd();
                                    return;
                                }}

                                // perform seek forward
                                ytPlayer.seekTo(next, true);
                            }} catch (e) {{
                                console.warn('fakeSpeedInterval error', e);
                            }}
                        }}, tick);
                    }}

                    // ensure end monitor running
                    startEndMonitor();
                }};

                if (window.YT && window.YT.Player) {{
                    window.onYouTubeIframeAPIReady();
                }}
            """
            )

            if self.show_speed_slider:

                def on_speed_change(_):
                    self.speed = speed_knob.value
                    ui.run_javascript(f"window.setYTSpeed({speed_knob.value});")

                with ui.row().classes("w-full items-center justify-center mt-2"):
                    speed_knob = (
                        ui.slider(
                            min=0.5,
                            max=8.0,
                            step=0.5,
                            value=self.speed,
                        )
                        .props("label-always")
                        .classes("w-full")
                        .on("change", on_speed_change)
                    )

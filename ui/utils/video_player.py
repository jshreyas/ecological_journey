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
                    speed: {self.speed}
                }};

                let ytPlayer;
                let ytEndInterval;
                let fakeSpeedInterval;

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
                    setYTSpeed(window.ytConfig.speed);
                    event.target.playVideo();
                    if (ytEndInterval) clearInterval(ytEndInterval);
                    ytEndInterval = setInterval(() => {{
                        const current = ytPlayer.getCurrentTime();
                        if (current >= window.ytConfig.end) {{
                            ytPlayer.pauseVideo();
                            clearInterval(ytEndInterval);
                            {js_on_end}
                        }}
                    }}, 500);
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

                    // clear any old intervals
                    if (fakeSpeedInterval) clearInterval(fakeSpeedInterval);

                    if (ytPlayer && ytPlayer.setPlaybackRate) {{
                        if (speed <= 2.0) {{
                            ytPlayer.setPlaybackRate(speed);
                        }} else {{
                            ytPlayer.setPlaybackRate(2.0); // max native
                            // simulate faster playback with seek hack
                            const tick = 100; // ms
                            fakeSpeedInterval = setInterval(() => {{
                                if (ytPlayer && ytPlayer.getCurrentTime) {{
                                    let cur = ytPlayer.getCurrentTime();
                                    ytPlayer.seekTo(cur + (speed * tick / 1000), true);
                                }}
                            }}, tick);
                        }}
                    }}
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

                with ui.row().classes("items-center justify-center mt-2 mx-6"):
                    speed_knob = (
                        ui.knob(
                            min=0.25,
                            max=8.0,  # 👈 allow up to 8x
                            step=0.25,
                            value=self.speed,
                            track_color="grey-2",
                            show_value=True,
                        )
                        .props("size=60")
                        .on("change", on_speed_change)
                    )

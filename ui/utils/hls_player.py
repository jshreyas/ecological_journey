import uuid

from nicegui import app, ui


class HLSPlayer:

    def __init__(
        self,
        hls_url: str,
        start: int = 0,
        end: int = 600,
        speed: float = 1.0,
        show_speed_slider: bool = True,
        width: int = 700,
        height: int = 400,
        on_end=None,
        parent=None,
    ):
        self.hls_url = hls_url
        self.start = start
        self.end = end
        self.speed = speed
        self.show_speed_slider = show_speed_slider
        self.width = width
        self.height = height
        self.on_end = on_end
        self.parent = parent
        self._render()

    def _render(self):
        self.element_id = f"hls-player-{uuid.uuid4().hex[:8]}"

        context = self.parent if self.parent else ui
        with context:
            ui.html(
                f"""
                    <div id="hls-player-wrapper" style="width: 100%; height: 100%; position: relative; overflow: hidden;">
                        <video id="{self.element_id}" controls style="border-radius: 12px; background: #000;"></video>
                    </div>"""
            )

            # 👇 Optional endpoint callback for on_end
            if self.on_end:
                endpoint = f"/_nicegui_api/{self.element_id}_on_end"

                @app.post(endpoint)
                async def _on_end_event():
                    if callable(self.on_end):
                        self.on_end()
                    return {"status": "ok"}

                js_on_end = f"""
                    fetch('/_nicegui_api/{self.element_id}_on_end', {{method: 'POST'}});
                """
            else:
                js_on_end = ""

            ui.add_body_html(
                f"""
            <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
            <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const video = document.getElementById('{self.element_id}');
                const speed = {self.speed};
                const start = {self.start};
                const end = {self.end};
                if (!video) {{
                    console.error('Video element not found');
                    return;
                }}
                if (Hls.isSupported()) {{
                    const hls = new Hls();
                    hls.loadSource("{self.hls_url}");
                    hls.attachMedia(video);
                    hls.on(Hls.Events.MANIFEST_PARSED, function() {{
                        video.currentTime = start;
                        video.playbackRate = speed;
                        video.play();
                    }});
                }} else if (video.canPlayType('application/vnd.apple.mpegurl')) {{
                    video.src = "{self.hls_url}";
                    video.playbackRate = speed;
                    video.currentTime = start;
                    video.play();
                }}
                // ⏱ End detection
                const interval = setInterval(() => {{
                    if (video.currentTime >= end) {{
                        video.pause();
                        clearInterval(interval);
                        {js_on_end}
                    }}
                }}, 500);

                // global speed setter
                window.setHLSSpeed = function(newSpeed) {{
                    video.playbackRate = newSpeed;
                }};
            }});
            </script>
            """
            )

            # 👇 Optional speed control knob
            if self.show_speed_slider:

                def on_speed_change(_):
                    self.speed = speed_knob.value
                    ui.run_javascript(f"window.setHLSSpeed({speed_knob.value});")

                with ui.row().classes("items-center justify-center mt-2 mx-6"):
                    speed_knob = (
                        ui.knob(
                            min=0.25,
                            max=8.0,
                            step=0.25,
                            value=self.speed,
                            track_color="grey-2",
                            show_value=True,
                        )
                        .props("size=60")
                        .on("change", on_speed_change)
                    )

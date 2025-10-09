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
        safe_id = uuid.uuid4().hex[:8]
        self.element_id = f"hls_player_{safe_id}"  # JS var-safe ID
        wrapper_id = f"hls_wrapper_{safe_id}"
        context = self.parent if self.parent else ui

        with context:
            # --- HTML container ---
            ui.html(
                f"""
                <div id="{wrapper_id}" style="width:{self.width}px;height:{self.height}px;position:relative;">
                    <video id="{self.element_id}" controls style="width:100%;height:100%;background:#000;border-radius:12px;"></video>
                </div>
            """
            )

            # --- End callback ---
            js_on_end = ""
            if self.on_end:
                endpoint = f"/_nicegui_api/{self.element_id}_on_end"

                @app.post(endpoint)
                async def _on_end_event():
                    if callable(self.on_end):
                        self.on_end()
                    return {"status": "ok"}

                js_on_end = f"fetch('{endpoint}',{{method:'POST'}});"

            # --- HLS JS ---
            ui.add_body_html(
                f"""
                <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
                <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    const video = document.getElementById('{self.element_id}');
                    const url = "{self.hls_url}?start={self.start}&end={self.end}&_=" + Date.now();
                    console.log("[HLSPlayer] Loading:", url);

                    const hlsVarName = "__currentHLS_{safe_id}";
                    if (window[hlsVarName]) {{
                        try {{
                            window[hlsVarName].stopLoad();
                            window[hlsVarName].detachMedia();
                            window[hlsVarName].destroy();
                            console.log("[HLSPlayer] Destroyed old HLS instance");
                        }} catch(e) {{
                            console.warn("[HLSPlayer] destroy() error:", e);
                        }}
                        delete window[hlsVarName];
                    }}

                    if (Hls.isSupported()) {{
                        const hls = new Hls({{
                            startFragPrefetch: true,
                            maxBufferLength: 20,
                            maxMaxBufferLength: 60,
                            maxBufferSize: 60 * 1000 * 1000,
                            maxBufferHole: 1.5,
                            liveSyncDurationCount: 3,
                            enableWorker: true,
                            lowLatencyMode: false,
                            autoStartLoad: true,
                            fragLoadTimeout: 300000,
                            manifestLoadingTimeOut: 90000,
                            levelLoadingTimeOut: 90000,
                        }});
                        window[hlsVarName] = hls;

                        hls.attachMedia(video);
                        hls.on(Hls.Events.MEDIA_ATTACHED, () => {{
                            console.log("[HLSPlayer] MEDIA_ATTACHED → load source");
                            hls.loadSource(url);
                        }});

                        // Play only after buffered enough
                        hls.on(Hls.Events.BUFFER_APPENDED, () => {{
                            if (video.buffered.length && video.buffered.end(0) > 5 && video.paused) {{
                                console.log("[HLSPlayer] Enough buffer → start playback");
                                video.playbackRate = {self.speed};
                                video.play().catch(err => console.warn("[HLSPlayer] play() error:", err));
                            }}
                        }});

                        hls.on(Hls.Events.ERROR, (evt, data) => {{
                            console.warn("[HLSPlayer] HLS error:", data.details);
                            if (data.type === 'mediaError' && data.details === 'bufferStalledError') {{
                                console.log("[HLSPlayer] Recovering from stall...");
                                video.play().catch(()=>{{}});
                                hls.startLoad();
                            }}
                            if (data.fatal) {{
                                console.error("[HLSPlayer] Fatal error, destroying HLS instance");
                                try {{ hls.destroy(); }} catch(e) {{}}
                            }}
                        }});

                        hls.on(Hls.Events.MANIFEST_PARSED, () => {{
                            console.log("[HLSPlayer] MANIFEST_PARSED");
                        }});
                    }} else if (video.canPlayType('application/vnd.apple.mpegurl')) {{
                        video.src = url;
                        video.playbackRate = {self.speed};
                        video.play().catch(err => console.warn("[HLSPlayer] native play error:", err));
                    }}

                    video.addEventListener('ended', function() {{
                        console.log("[HLSPlayer] Clip ended");
                        {js_on_end}
                    }});

                    window['setHLSSpeed_{safe_id}'] = (s) => {{
                        video.playbackRate = s;
                        console.log("[HLSPlayer] Speed set to", s);
                    }};
                }});
                </script>
            """
            )

            # --- Speed Slider ---
            if self.show_speed_slider:

                def on_speed_change(_):
                    self.speed = knob.value
                    ui.run_javascript(f"window.setHLSSpeed_{safe_id}({self.speed});")

                with ui.row().classes("items-center justify-center mt-2 mx-6"):
                    knob = (
                        ui.knob(min=0.25, max=8.0, step=0.25, value=self.speed, show_value=True)
                        .props("size=60")
                        .on("change", on_speed_change)
                    )

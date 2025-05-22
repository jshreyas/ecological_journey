from nicegui import ui
from urllib.parse import urlparse, parse_qs


class VideoPlayer:

    def __init__(self, video_url: str, start: int = 0, end: int = 1000000, speed: float = 1.0, show_speed_slider: bool = True, width: int = 700, height: int = 400):
        self.video_id = self._extract_video_id(video_url)
        self.start = start
        self.end = end
        self.speed = speed
        self.show_speed_slider = show_speed_slider
        self.width = width
        self.height = height
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
        ui.html(f'''
            <div id="yt-player-wrapper">
                <div id="yt-player"></div>
            </div>
        ''')

        ui.add_head_html('''
            <script src="https://www.youtube.com/iframe_api"></script>
        ''')

        ui.run_javascript(f'''
            window.ytConfig = {{
                videoId: "{self.video_id}",
                start: {self.start},
                end: {self.end},
                speed: {self.speed}
            }};

            let ytPlayer;
            let ytEndInterval;

            window.onYouTubeIframeAPIReady = function() {{
                ytPlayer = new YT.Player('yt-player', {{
                    height: '{self.height}',
                    width: '{self.width}',
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
                event.target.setPlaybackRate(window.ytConfig.speed);
                event.target.playVideo();
                if (ytEndInterval) clearInterval(ytEndInterval);
                ytEndInterval = setInterval(() => {{
                    const current = ytPlayer.getCurrentTime();
                    if (current >= window.ytConfig.end) {{
                        ytPlayer.pauseVideo();
                        clearInterval(ytEndInterval);
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
                    }}
                }}, 500);
            }};

            window.setYTSpeed = function(speed) {{
                window.ytConfig.speed = speed;
                if (ytPlayer && ytPlayer.setPlaybackRate) {{
                    ytPlayer.setPlaybackRate(speed);
                }}
            }};

            if (window.YT && window.YT.Player) {{
                window.onYouTubeIframeAPIReady();
            }}
        ''')

        if self.show_speed_slider:
            def on_speed_change(_):
                self.speed = speed_knob.value
                ui.run_javascript(f"window.setYTSpeed({speed_knob.value});")
            with ui.row().classes('items-center gap-2'):
                speed_knob = ui.knob(
                    min=0.25, max=2.0, step=0.25, value=self.speed,
                    color='orange', track_color='grey-2', show_value=True
                ).props('size=60').on('change', on_speed_change)
                ui.label('Speed').classes('ml-2 text-xs text-gray-500')
from nicegui import ui
from urllib.parse import urlparse, parse_qs


class VideoPlayer:

    def __init__(self, video_url: str, start: int = 0, end: int = 1000000):
        self.video_id = self._extract_video_id(video_url)
        self.start = start
        self.end = end
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
        # Player container
        ui.html('<div id="yt-player-wrapper" class=" mx-auto"><div id="yt-player"></div></div>')

        # Load YouTube IFrame API
        ui.add_head_html('''
            <script src="https://www.youtube.com/iframe_api"></script>
        ''')

        # JS config and player logic
        ui.run_javascript(f'''
            window.ytConfig = {{
                videoId: "{self.video_id}",
                start: {self.start},
                end: {self.end}
            }};

            let ytPlayer;
            let ytEndInterval;

            window.onYouTubeIframeAPIReady = function() {{
                ytPlayer = new YT.Player('yt-player', {{
                    height: '400',
                    width: '700',
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

            function onPlayerStateChange(event) {{
                // Optionally handle state changes
            }}

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

            if (window.YT && window.YT.Player) {{
                window.onYouTubeIframeAPIReady();
            }}
        ''')
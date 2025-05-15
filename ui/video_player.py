from nicegui import ui
from urllib.parse import urlparse, parse_qs


class VideoPlayer:

    def __init__(self, video_url: str, start: int = 0, width: int = 560, height: int = 315):
        self.video_id = self._extract_video_id(video_url)
        self.start = start
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
        start_param = f"&start={self.start}" if self.start else ""
        embed_url = f"https://www.youtube.com/embed/{self.video_id}?autoplay=1{start_param}"
        ui.html(f'''
            <iframe width="{self.width}" height="{self.height}"
                src="{embed_url}"
                title="YouTube video player"
                frameborder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowfullscreen>
            </iframe>
        ''')

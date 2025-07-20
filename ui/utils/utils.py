# utils.py
from nicegui import ui
import requests
from utils.utils_notion import generate_tree
from datetime import datetime
from utils.cache import cache_get, cache_set


#TODO: Persist the notion tree in the mongodb
def get_notion_tree(recache: bool = False):
    """Fetch the Notion tree structure from the cache or generate it if not cached."""
    cached_tree = cache_get('notion_tree')
    if not recache and cached_tree:
        return cached_tree

    # Generate the tree structure
    tree = generate_tree()

    cache_set('notion_tree', tree)
    return tree

def format_time(seconds):
    minutes = seconds // 60
    sec = seconds % 60
    return f"{int(minutes):02}:{int(sec):02}"


# --- Helper: Group videos by YYYY-MM-DD ---
def group_videos_by_day(videos):
    """Group videos by date (YYYY-MM-DD) extracted from the timestamp."""
    grouped = {}
    for v in videos:
        # Extract the date portion from the timestamp
        video_date = datetime.strptime(v['date'], '%Y-%m-%dT%H:%M:%SZ').date().isoformat()
        grouped.setdefault(video_date, []).append(v)
    return grouped

# def embed_youtube_player(video_id: str, start: int = 0, end: int = None, speed: float = 1.0):
#     end_js = f"{end}" if end is not None else "null"
#     html_code = f"""
#     <div id="player"></div>
#     <script>
#       // Load the YouTube iframe API once
#       if (!window.YT) {{
#         var tag = document.createElement('script');
#         tag.src = "https://www.youtube.com/iframe_api";
#         var firstScriptTag = document.getElementsByTagName('script')[0];
#         firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
#       }}

#       // Wait for the API to be ready
#       function createPlayer() {{
#         player = new YT.Player('player', {{
#           height: '360',
#           width: '100%',
#           videoId: '{video_id}',
#           playerVars: {{
#             'rel': 0,
#             'modestbranding': 1
#           }},
#           events: {{
#             'onReady': function(event) {{
#               player.seekTo({start}, true);
#               player.setPlaybackRate({speed});
#               player.playVideo();

#               if ({end_js}) {{
#                 const stopInterval = setInterval(() => {{
#                   if (player.getCurrentTime() >= {end_js}) {{
#                     player.pauseVideo();
#                     clearInterval(stopInterval);
#                   }}
#                 }}, 200);
#               }}
#             }}
#           }}
#         }});
#       }}

#       // Attach to global scope so API can find it
#       window.onYouTubeIframeAPIReady = function() {{
#         createPlayer();
#       }};

#       // If API is already loaded, call directly
#       if (window.YT && window.YT.Player) {{
#         createPlayer();
#       }}
#     </script>
#     """
#     ui.html(html_code).classes('w-full h-[400px]')

def embed_youtube_player(video_id: str, start=0, end: int = None, speed: float = 1.0):
    url = f"https://www.youtube.com/embed/{video_id}?start={start}&rel=0&modestbranding=1&autoplay=1"
    iframe_html = f'''
        <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden;">
            <iframe src="{url}"
                    style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
                    frameborder="0"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowfullscreen>
            </iframe>
        </div>
    '''
    ui.html(iframe_html).classes("w-full max-w-5xl mx-auto")


# TODO: update the video embed window based on the orientation
def get_video_orientation_internal(video_id: str) -> str:
    url = "https://www.youtube.com/youtubei/v1/player"
    params = {
        "videoId": video_id
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.youtube.com"
    }
    payload = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20210721.00.00"
            }
        },
        "videoId": video_id
    }

    response = requests.post(url, params=params, json=payload, headers=headers)
    data = response.json()

    try:
        streaming_data = data.get("streamingData", {})
        formats = streaming_data.get("formats", [])

        # Get the first video format that includes width & height
        for fmt in formats:
            width = fmt.get("width")
            height = fmt.get("height")
            if width and height:
                return "portrait" if height > width else "landscape"

        return "Unknown (no resolution data found)"
    except Exception as e:
        return f"Error: {str(e)}"

# --- Utility for parsing and checking query syntax ---
def parse_query_expression(tokens):
    # Precedence: NOT > AND > OR

    def parse(tokens):
        def parse_not(index):
            if tokens[index] == 'NOT':
                sub_expr, next_index = parse_not(index + 1)
                return ('NOT', sub_expr), next_index
            else:
                return tokens[index], index + 1

        def parse_and(index):
            left, index = parse_not(index)
            while index < len(tokens) and tokens[index] == 'AND':
                right, index = parse_not(index + 1)
                left = ('AND', left, right)
            return left, index

        def parse_or(index):
            left, index = parse_and(index)
            while index < len(tokens) and tokens[index] == 'OR':
                right, index = parse_and(index + 1)
                left = ('OR', left, right)
            return left, index

        ast, _ = parse_or(0)
        return ast

    def evaluate_ast(ast, clip_labels):
        if isinstance(ast, str):
            return ast in clip_labels
        if isinstance(ast, tuple):
            op = ast[0]
            if op == 'NOT':
                return not evaluate_ast(ast[1], clip_labels)
            elif op == 'AND':
                return evaluate_ast(ast[1], clip_labels) and evaluate_ast(ast[2], clip_labels)
            elif op == 'OR':
                return evaluate_ast(ast[1], clip_labels) or evaluate_ast(ast[2], clip_labels)
        return True  # Fallback

    ast = parse(tokens)

    def evaluate(clip_labels):
        return evaluate_ast(ast, clip_labels)

    return evaluate

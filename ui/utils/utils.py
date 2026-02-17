# utils.py
from datetime import datetime

import requests
from nicegui import ui


def navigate_to_film(video_id, clip_id=None):
    url = f"/film/{video_id}"
    if clip_id:
        url += f"?clip={clip_id}"
    ui.navigate.to(url)


def format_time(t: int) -> str:
    hours, remainder = divmod(t, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


# --- Helper: Group videos by YYYY-MM-DD ---
def group_videos_by_day(videos):
    """Group videos by date (YYYY-MM-DD) extracted from the timestamp."""
    grouped = {}
    for v in videos:
        # Extract the date portion from the timestamp
        video_date = datetime.strptime(v["date"], "%Y-%m-%dT%H:%M:%SZ").date().isoformat()
        grouped.setdefault(video_date, []).append(v)
    return grouped


# TODO: update the video embed window based on the orientation
def get_video_orientation_internal(video_id: str) -> str:
    url = "https://www.youtube.com/youtubei/v1/player"
    params = {"videoId": video_id}
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.youtube.com",
    }
    payload = {
        "context": {"client": {"clientName": "WEB", "clientVersion": "2.20210721.00.00"}},
        "videoId": video_id,
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
            if tokens[index] == "NOT":
                sub_expr, next_index = parse_not(index + 1)
                return ("NOT", sub_expr), next_index
            else:
                return tokens[index], index + 1

        def parse_and(index):
            left, index = parse_not(index)
            while index < len(tokens) and tokens[index] == "AND":
                right, index = parse_not(index + 1)
                left = ("AND", left, right)
            return left, index

        def parse_or(index):
            left, index = parse_and(index)
            while index < len(tokens) and tokens[index] == "OR":
                right, index = parse_and(index + 1)
                left = ("OR", left, right)
            return left, index

        ast, _ = parse_or(0)
        return ast

    def evaluate_ast(ast, clip_labels):
        if isinstance(ast, str):
            return ast in clip_labels
        if isinstance(ast, tuple):
            op = ast[0]
            if op == "NOT":
                return not evaluate_ast(ast[1], clip_labels)
            elif op == "AND":
                return evaluate_ast(ast[1], clip_labels) and evaluate_ast(ast[2], clip_labels)
            elif op == "OR":
                return evaluate_ast(ast[1], clip_labels) or evaluate_ast(ast[2], clip_labels)
        return True  # Fallback

    ast = parse(tokens)

    def evaluate(clip_labels):
        return evaluate_ast(ast, clip_labels)

    return evaluate


def human_stamp(ts: str) -> str:
    if ts.endswith("Z"):
        ts = ts.replace("Z", "+00:00")

    dt = datetime.fromisoformat(ts)
    return dt.strftime("%b %d, %I:%M %p")  # e.g. "Sep 23, 12:29 AM"

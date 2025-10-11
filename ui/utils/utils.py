# utils.py
import json
from datetime import datetime

import requests
from nicegui import ui


def navigate_to_film(video_id, clip_id=None):
    url = f"/film/{video_id}"
    if clip_id:
        url += f"?clip={clip_id}"
    ui.navigate.to(url)


def format_time(seconds):
    minutes = seconds // 60
    sec = seconds % 60
    return f"{int(minutes):02}:{int(sec):02}"


def parse_cached_logs(value: list[str]) -> list[str]:
    """Parse Redis logs into clean UI-printable lines."""
    clean_logs = []
    for raw in value:
        try:
            # Step 1: handle double-encoded JSON
            if isinstance(raw, str) and raw.startswith('"'):
                raw = json.loads(raw)
            # Step 2: decode actual JSON dict
            entry = json.loads(raw)
            timestamp = entry.get("t", "")
            msg = entry.get("msg", "")
            # Optional: prettify timestamp
            time_str = human_stamp(timestamp)
            # time_str = datetime.fromisoformat(timestamp).strftime("%H:%M:%S")
            clean_logs.append(f"{time_str} | {msg}")
        except Exception:
            clean_logs.append(f"[decode error] {raw}")
    return list(reversed(clean_logs))  # Redis LPUSH adds newest first


def parse_flexible_datetime(ts: str) -> datetime:
    """Parse a timestamp that may have Z, fractional seconds, or timezone info."""
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d %H:%M:%S.%f%z"):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue

    # Fallback: ISO parser (handles most variations)
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        raise ValueError(f"Unrecognized timestamp format: {ts}")


def group_videos_by_day(videos):
    """Group videos by date (YYYY-MM-DD) extracted from timestamp.
    Supports timestamps with or without milliseconds and with timezone info.
    """
    grouped = {}
    for v in videos:
        ts = v["date"]
        dt = None

        # Try multiple timestamp formats
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d %H:%M:%S.%f%z"):
            try:
                dt = datetime.strptime(ts, fmt)
                break
            except ValueError:
                continue

        # Fallback: try Python’s built-in ISO parser (handles most edge cases)
        if dt is None:
            try:
                dt = datetime.fromisoformat(ts)
            except Exception:
                print(f"⚠️ Skipping unrecognized timestamp format: {ts}")
                continue

        video_date = dt.date().isoformat()
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
    dt = datetime.fromisoformat(ts)
    return dt.strftime("%b %d, %I:%M %p")  # e.g. "Sep 23, 12:29 AM"

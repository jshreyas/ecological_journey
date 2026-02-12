import asyncio
import os
import re
from datetime import datetime

import dateparser
import httpx
import isodate
import pytz
from dotenv import load_dotenv

from ui.log import log

load_dotenv()
BASE_URL = "https://www.googleapis.com/youtube/v3"
UTC = pytz.utc

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("Missing API_KEY in environment variables")


# ---------- regex patterns ----------
RE_YYYYMMDDHHMMSS = re.compile(r"\b(20\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\b")
RE_YYYYMMDD = re.compile(r"\b(20\d{2})(\d{2})(\d{2})\b")
RE_ISO_DATE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
RE_MM_DD = re.compile(r"\b(\d{1,2})\s+(\d{1,2})\b")


def parse_training_date_from_title(
    title: str,
    upload_date_iso: str | None = None,
):
    """
    Extract training date from title.
    upload_date_iso is required for MM DD inference.

    Returns UTC ISO string or None.
    """

    upload_dt = None
    if upload_date_iso:
        upload_dt = datetime.fromisoformat(upload_date_iso.replace("Z", "+00:00")).astimezone(UTC)

    now = datetime.now(UTC)

    # 1️⃣ YYYYMMDDHHMMSS
    m = RE_YYYYMMDDHHMMSS.search(title)
    if m:
        dt = datetime(
            int(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
            tzinfo=UTC,
        )
        if dt <= now:
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 2️⃣ YYYYMMDD
    m = RE_YYYYMMDD.search(title)
    if m:
        dt = datetime(
            int(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
            tzinfo=UTC,
        )
        if dt <= now:
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 3️⃣ ISO YYYY-MM-DD
    m = RE_ISO_DATE.search(title)
    if m:
        try:
            dt = datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=UTC)
            if dt <= now:
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass

    # 4️⃣ MM DD (infer year from upload date)
    m = RE_MM_DD.search(title)
    if m and upload_dt:
        month = int(m.group(1))
        day = int(m.group(2))

        # Try upload year first
        for year in (upload_dt.year, upload_dt.year - 1):
            try:
                candidate = datetime(year, month, day, tzinfo=UTC)
            except ValueError:
                continue

            # Training must be before upload (or very close)
            if candidate <= upload_dt:
                return candidate.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 5️⃣ Fuzzy fallback (dateparser)
    dt = dateparser.parse(
        title,
        settings={
            "RETURN_AS_TIMEZONE_AWARE": True,
            "TO_TIMEZONE": "UTC",
            "PREFER_DATES_FROM": "past",
            "RELATIVE_BASE": upload_dt or now,
        },
    )

    if dt:
        if dt.year >= 2000 and dt <= now:
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return None


async def fetch_videos_metadata(
    client: httpx.AsyncClient,
    video_ids: list[str],
):
    results = {}

    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]  # noqa: E203
        ids = ",".join(chunk)

        resp = await client.get(
            f"{BASE_URL}/videos",
            params={
                "part": "snippet,contentDetails",
                "id": ids,
                "key": API_KEY,
            },
            timeout=20,
        )

        resp.raise_for_status()

        for item in resp.json().get("items", []):
            vid = item["id"]

            duration_raw = item.get("contentDetails", {}).get("duration")
            if not duration_raw:
                log.warning(f"[YT SYNC] Missing duration for video {vid}")
                continue

            seconds = isodate.parse_duration(duration_raw).total_seconds()

            # 🔥 Treat PT0S as incomplete sync
            if seconds <= 0:
                log.error(f"[YT SYNC] Skipping video {vid} (duration={duration_raw}) " f"— likely still processing.")
                continue

            results[vid] = {
                "upload_date": item["snippet"]["publishedAt"],
                "duration_seconds": seconds,
            }

    return results


async def fetch_playlist_items_single(
    client: httpx.AsyncClient,
    playlist_id: str,
    latest_saved_date: str | None = None,
    existing_video_ids: set[str] | None = None,
):
    items = []
    video_ids = []
    page_token = None
    latest_saved_date_dt = None

    if latest_saved_date:
        latest_saved_date_dt = datetime.fromisoformat(latest_saved_date.replace("Z", "+00:00"))

    while True:
        resp = await client.get(
            f"{BASE_URL}/playlistItems",
            params={
                "part": "snippet",
                "maxResults": 50,
                "playlistId": playlist_id,
                "pageToken": page_token,
                "key": API_KEY,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()

        page_has_newer_video = False

        for item in data.get("items", []):
            snippet = item["snippet"]

            if snippet["title"].strip() == "Deleted video" and not snippet.get("thumbnails"):
                continue

            playlist_added = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))

            vid = snippet["resourceId"]["videoId"]

            # Skip already saved
            if existing_video_ids and vid in existing_video_ids:
                continue

            # Skip old videos (DO NOT break)
            if latest_saved_date_dt and playlist_added < latest_saved_date_dt:
                continue

            page_has_newer_video = True

            items.append(
                {
                    "video_id": vid,
                    "title": snippet["title"],
                }
            )
            video_ids.append(vid)

        page_token = data.get("nextPageToken")

        # Optimization:
        # If no videos in this page were newer AND no next page → stop
        if not page_token:
            break

        # If the entire page was older than latest_saved_date
        # AND we already processed some newer pages before,
        # then it's safe to stop.
        if latest_saved_date_dt and not page_has_newer_video:
            break

    return items, video_ids


async def fetch_playlist_items(
    playlists: list[dict],
    concurrency: int = 5,
):
    """
    playlists = [
      {
        "_id": "...",
        "playlist_id": "...",
        "latest_saved_date": str | None
        "existing_video_ids": list[str] | None
      }
    ]
    """

    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient() as client:

        async def guarded_fetch(p):
            async with semaphore:
                return p, await fetch_playlist_items_single(
                    client,
                    p["playlist_id"],
                    p.get("latest_saved_date", None),
                    set(p.get("existing_video_ids", [])),
                )

        tasks = [guarded_fetch(p) for p in playlists]
        results = await asyncio.gather(*tasks)

        all_video_ids = []
        per_playlist = {}

        for p, (items, vids) in results:
            per_playlist[p["_id"]] = items
            all_video_ids.extend(vids)

        metadata = await fetch_videos_metadata(
            client,
            list(set(all_video_ids)),
        )

        # Assemble final payload
        output = {}

        for pid, items in per_playlist.items():
            videos = []
            for item in items:
                meta = metadata.get(item["video_id"])
                if not meta:
                    continue

                videos.append(
                    {
                        "video_id": item["video_id"],
                        "title": item["title"],
                        "youtube_url": f"https://www.youtube.com/watch?v={item['video_id']}",
                        "date": meta["upload_date"],  # upload date
                        "training_date": parse_training_date_from_title(
                            title=item["title"], upload_date_iso=meta["upload_date"]
                        ),
                        "duration_seconds": meta["duration_seconds"],
                        "type": "",
                        "partners": [],
                        "positions": [],
                        "notes": "",
                        "labels": [],
                        "clips": [],
                    }
                )

            output[pid] = videos

        return output


async def fetch_playlist_metadata(
    playlist_id: str,
    client: httpx.AsyncClient | None = None,
) -> dict | None:
    """
    Fetch playlist snippet metadata using YouTube Data API.

    Returns:
      {
        "title": str,
        "description": str,
        "publishedAt": str,
        "channelTitle": str,
        ...
      }
    or None if not found / inaccessible
    """

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{BASE_URL}/playlists",
                params={
                    "part": "snippet",
                    "id": playlist_id,
                    "key": API_KEY,
                },
            )
            resp.raise_for_status()

            items = resp.json().get("items", [])
            if not items:
                return None

            return items[0]["snippet"]

        except httpx.HTTPError:
            return None

import hashlib
import json
from collections import defaultdict
from typing import Any, Dict, List

from ui.log import log
from ui.utils.cache import cache_del, cache_get, cache_set
from ui.utils.utils_api import load_videos

INDEX_TTL_SECONDS = 60 * 60 * 24  # 24 hours


class SearchIndexService:
    ACTIVE_INDEX_POINTER = "search:active_index"

    # -----------------------------------------
    # PUBLIC
    # -----------------------------------------

    def build_and_cache_index(self) -> str:
        videos = load_videos()
        db_hash = self._compute_db_state_hash(videos)
        index_key = f"search:index:{db_hash}"

        existing = cache_get(index_key)
        if existing:
            log.info(f"Search index already exists for hash {db_hash}")
            cache_set(self.ACTIVE_INDEX_POINTER, index_key)
            return index_key

        log.info(f"Building new search index for hash {db_hash}")

        index_data = self._build_index(videos)

        cache_set(index_key, index_data, ex=INDEX_TTL_SECONDS)
        cache_set(self.ACTIVE_INDEX_POINTER, index_key)

        return index_key

    def get_active_index(self) -> Dict[str, Any] | None:
        index_key = cache_get(self.ACTIVE_INDEX_POINTER)
        if not index_key:
            return None
        return cache_get(index_key)

    def invalidate_all_indexes(self):
        active = cache_get(self.ACTIVE_INDEX_POINTER)
        if active:
            cache_del(active)
        cache_del(self.ACTIVE_INDEX_POINTER)

    # -----------------------------------------
    # INTERNAL
    # -----------------------------------------

    def _compute_db_state_hash(self, videos: List[Dict]) -> str:
        raw = json.dumps(
            [(v["video_id"], v["date"], len(v.get("anchors", [])), len(v.get("clips", []))) for v in videos],
            sort_keys=True,
        )
        return hashlib.md5(raw.encode()).hexdigest()

    def _build_index(self, videos: List[Dict]) -> Dict[str, Any]:
        rows = {}
        index = {
            "by_type": defaultdict(list),
            "by_label": defaultdict(list),
            "by_partner": defaultdict(list),
            "by_playlist": defaultdict(list),
            "by_date": defaultdict(list),
        }

        for v in videos:
            date_key = v["date"][:10]
            # Always add a video-level row (so videos with anchors/clips are represented)
            row = self._make_row(v, "video", None, None)
            self._index_row(row, rows, index, date_key)

            # Then add anchors and clips as separate rows
            for a in v.get("anchors", []):
                row = self._make_row(v, "anchor", a["start"], None, a)
                self._index_row(row, rows, index, date_key)

            for c in v.get("clips", []):
                row = self._make_row(v, "clip", c["start"], c["end"], c)
                self._index_row(row, rows, index, date_key)

        return {"rows": rows, "index": index}

    def _make_row(self, video, type_, start, end, child=None):
        row_id = f"{type_}_{video['video_id']}_{start or 0}"
        # Thumbnail: prefer provided thumbnail_url, otherwise try YouTube pattern
        thumbnail = video.get("thumbnail_url") or f"https://i.ytimg.com/vi/{video['video_id']}/hqdefault.jpg"

        return {
            "id": row_id,
            "type": type_,
            "video_id": video["video_id"],
            "title": video["title"],
            "playlist": video.get("playlist_name", ""),
            "playlist_description": video.get("playlist_description", ""),
            "date": video["date"],
            "start": start,
            "end": end,
            "duration": (end - start) if end else video.get("duration_seconds"),
            "description": child.get("description") if child else video.get("notes", ""),
            "labels": child.get("labels", []) if child else video.get("labels", []),
            "partners": child.get("partners", []) if child else video.get("partners", []),
            "thumbnail": thumbnail,
        }

    def _index_row(self, row, rows, index, date_key):
        rid = row["id"]
        rows[rid] = row

        index["by_type"][row["type"]].append(rid)
        index["by_playlist"][row["playlist"]].append(rid)
        index["by_date"][date_key].append(rid)

        for label in row["labels"]:
            index["by_label"][label].append(rid)

        for partner in row["partners"]:
            index["by_partner"][partner].append(rid)

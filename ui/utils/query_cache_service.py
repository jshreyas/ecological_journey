from typing import List

from ui.utils.cache import cache_get, cache_set

QUERY_TTL_SECONDS = 60 * 10  # 10 minutes


class QueryCacheService:

    def get(self, user_id: str, query: str) -> List[str] | None:
        key = self._make_key(user_id, query)
        return cache_get(key)

    def set(self, user_id: str, query: str, result_ids: List[str]):
        key = self._make_key(user_id, query)
        cache_set(key, result_ids, ex=QUERY_TTL_SECONDS)

    def _make_key(self, user_id: str, query: str):
        normalized = query.strip().lower()
        return f"search:query:{user_id}:{normalized}"

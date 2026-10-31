from unittest.mock import Mock

from ui.utils import cache as cache_module


def test_cache_result_caches_the_computed_value(monkeypatch):
    cache_module._cache.clear()
    cache_set = Mock()
    monkeypatch.setattr(cache_module, "cache_get", Mock(return_value=None))
    monkeypatch.setattr(cache_module, "cache_set", cache_set)
    compute = Mock(return_value={"name": "playlist"})

    @cache_module.cache_result("playlist:1", ttl_seconds=30)
    def load_playlist():
        return compute()

    first = load_playlist()
    second = load_playlist()

    assert first == second == {"name": "playlist"}
    compute.assert_called_once_with()
    cache_set.assert_called_once_with("playlist:1", {"name": "playlist"}, 30)


def test_invalidate_cache_removes_resolved_keys_after_success(monkeypatch):
    cache_module._cache.clear()
    cache_module._cache["video:1"] = {"title": "stale"}
    cache_del = Mock()
    monkeypatch.setattr(cache_module, "cache_del", cache_del)

    @cache_module.invalidate_cache(keys=lambda video_id: [f"video:{video_id}"])
    def update_video(video_id):
        return {"video_id": video_id}

    result = update_video("1")

    assert result == {"video_id": "1"}
    assert "video:1" not in cache_module._cache
    cache_del.assert_called_once_with("video:1")

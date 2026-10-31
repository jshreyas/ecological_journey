from unittest.mock import Mock

from ui.pages import search as search_module
from ui.pages.search import State, VideosTab


def test_search_state_caches_video_and_clip_data(monkeypatch):
    videos = [{"video_id": "video-1"}]
    clips = [{"clip_id": "clip-1"}]
    load_videos = Mock(return_value=videos)
    load_clips = Mock(return_value=clips)
    monkeypatch.setattr(search_module, "load_videos", load_videos)
    monkeypatch.setattr(search_module, "load_clips", load_clips)
    state = State()

    assert state.load_videos() is videos
    assert state.load_videos() is videos
    assert state.load_clips() is clips
    assert state.load_clips() is clips
    load_videos.assert_called_once_with()
    load_clips.assert_called_once_with()


def test_videos_tab_builds_sorted_rows_and_duration_strings(monkeypatch):
    videos = [
        {
            "video_id": "older",
            "title": "Older video",
            "date": "2024-01-01T00:00:00Z",
            "duration_seconds": 75,
            "clips": [],
            "anchors": [],
        },
        {
            "video_id": "newer",
            "title": "Newer video",
            "date": "2024-02-01T00:00:00Z",
            "duration_seconds": 3661,
            "clips": [{"clip_id": "clip-1"}],
            "anchors": [{"anchor_id": "anchor-1"}],
            "playlist_name": "Training",
            "notes": "Notes",
        },
    ]
    state = Mock()
    state.load_videos.return_value = videos
    container = Mock()
    container.__enter__ = Mock(return_value=container)
    container.__exit__ = Mock(return_value=None)
    grid = Mock()
    grid.classes.return_value = grid
    aggrid = Mock(return_value=grid)
    monkeypatch.setattr(search_module.ui, "aggrid", aggrid)
    tab = VideosTab(state)

    tab.create_tab(container)

    assert [row["video_id"] for row in tab.rows] == ["newer", "older"]
    assert tab.rows[0]["duration"] == "1:01:01"
    assert tab.rows[0]["clip_count"] == 1
    assert tab.rows[0]["anchor_count"] == 1
    assert "film/newer" in tab.rows[0]["thumbnail"]
    aggrid.assert_called_once()

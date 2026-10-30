from unittest.mock import AsyncMock, Mock

import pytest

from ui.pages.components.home import playlist_tab as playlist_tab_module
from ui.pages.components.home.playlist_tab import SYNC_ERROR, SYNC_NOOP, SYNC_OK, PlaylistTab


def test_build_playlist_rows_reflects_ownership():
    tab = PlaylistTab(Mock())

    rows = tab._build_playlist_rows(
        [
            {"_id": "owned", "name": "Owned", "video_count": 3, "color": "blue"},
            {"_id": "shared", "name": "Shared", "video_count": 1, "color": "red"},
        ],
        owned_ids={"owned"},
        logged_in=True,
    )

    assert rows[0]["can_sync"] is True
    assert rows[0]["is_owned"] is True
    assert rows[0]["video_count"] == 3
    assert rows[1]["can_sync"] is False
    assert rows[1]["is_owned"] is False


@pytest.mark.asyncio
async def test_sync_playlist_adds_new_videos_and_returns_success(monkeypatch):
    state = Mock()
    state.load_videos_by_playlist.return_value = [{"date": "2024-01-01", "video_id": "old"}]
    state.create_video.return_value = {"success": True}
    fetch_items = AsyncMock(return_value={"playlist-1": [{"video_id": "new"}]})
    monkeypatch.setattr(playlist_tab_module, "fetch_playlist_items", fetch_items)
    tab = PlaylistTab(state)
    playlist = {"_id": "playlist-1", "name": "Training", "playlist_id": "source"}

    result = await tab.sync_playlist(playlist)

    assert result == SYNC_OK
    assert playlist["latest_saved_date"] == "2024-01-01"
    assert playlist["existing_video_ids"] == ["old"]
    fetch_items.assert_awaited_once_with([playlist])
    state.create_video.assert_called_once_with([{"video_id": "new"}], "playlist-1")


@pytest.mark.asyncio
async def test_sync_playlist_returns_noop_when_there_are_no_new_videos(monkeypatch):
    state = Mock()
    state.load_videos_by_playlist.return_value = []
    fetch_items = AsyncMock(return_value={"playlist-1": []})
    monkeypatch.setattr(playlist_tab_module, "fetch_playlist_items", fetch_items)
    tab = PlaylistTab(state)

    result = await tab.sync_playlist({"_id": "playlist-1", "name": "Training", "playlist_id": "source"})

    assert result == SYNC_NOOP
    state.create_video.assert_not_called()


@pytest.mark.asyncio
async def test_sync_playlist_reports_fetch_errors(monkeypatch):
    state = Mock()
    state.load_videos_by_playlist.return_value = []
    monkeypatch.setattr(
        playlist_tab_module,
        "fetch_playlist_items",
        AsyncMock(side_effect=RuntimeError("YouTube unavailable")),
    )
    tab = PlaylistTab(state)

    result = await tab.sync_playlist({"_id": "playlist-1", "name": "Training", "playlist_id": "source"})

    assert result == SYNC_ERROR
    state.create_video.assert_not_called()

from unittest.mock import Mock

from ui.data.models import User
from ui.pages.components.home import state as home_state_module
from ui.pages.components.home.state import State


def test_home_state_caches_loaded_data_and_refreshes_callbacks(monkeypatch):
    user = User(username="alice", email="alice@example.com")
    videos = [{"video_id": "video-1"}]
    playlists = [{"_id": "playlist-1"}]
    load_videos = Mock(return_value=videos)
    load_playlists = Mock(return_value=playlists)
    load_playlists_for_user = Mock(return_value={"owned": playlists, "member": []})
    monkeypatch.setattr(home_state_module, "lvs", load_videos)
    monkeypatch.setattr(home_state_module, "lp", load_playlists)
    monkeypatch.setattr(home_state_module, "lp_user", load_playlists_for_user)
    state = State(user=user)
    callback = Mock()
    state.add_refresh_callback(callback)

    assert state.load_videos() is videos
    assert state.load_videos() is videos
    assert state.load_playlists() is playlists
    assert state.load_playlists_for_user() == {"owned": playlists, "member": []}
    assert state.load_playlists_for_user() == {"owned": playlists, "member": []}
    load_videos.assert_called_once_with()
    load_playlists.assert_called_once_with()
    load_playlists_for_user.assert_called_once_with(str(user.id))

    state.refresh()

    assert load_videos.call_count == 2
    assert load_playlists.call_count == 2
    assert state._load_playlists_user is None
    callback.assert_called_once_with()


def test_home_state_generates_stable_date_and_video_anchors():
    state = State()

    assert state.get_date_anchor("2024-04-15T12:30:00Z") == "date-2024-04-15"
    assert state.get_video_anchor("video-1") == "video-video-1"

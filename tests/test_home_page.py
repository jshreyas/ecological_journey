"""
Unit tests for Home Page components
"""

from unittest.mock import MagicMock, Mock

import pytest

from ui.pages import home as home_module
from ui.pages.home import with_user_context
from ui.utils.user_context import User


@pytest.fixture(autouse=True)
def patch_nicegui_contexts(monkeypatch):
    # Patch all NiceGUI context manager UI calls to MagicMock with context support
    for name in ["column", "row", "card", "tabs", "tab_panels", "tab_panel", "splitter"]:
        mock_cm = MagicMock()
        mock_cm.return_value = mock_cm
        mock_cm.__enter__.return_value = mock_cm
        mock_cm.__exit__.return_value = None
        monkeypatch.setattr(home_module.ui, name, mock_cm)
    return None


@pytest.fixture
def mock_ui(monkeypatch):
    mock_ui = MagicMock()
    monkeypatch.setattr(home_module, "ui", mock_ui)
    return mock_ui


@pytest.fixture
def mock_app(monkeypatch):
    mock_app = MagicMock()
    monkeypatch.setattr(home_module, "app", mock_app)
    return mock_app


@pytest.fixture
def mock_utils(monkeypatch):
    monkeypatch.setattr(
        home_module, "load_playlists", Mock(return_value=[{"_id": "pl1", "name": "Test Playlist", "videos": [1, 2]}])
    )
    monkeypatch.setattr(
        home_module,
        "load_playlists_for_user",
        Mock(
            return_value={
                "owned": [{"_id": "pl1", "name": "Test Playlist", "videos": [1, 2], "playlist_id": "pl1"}],
                "member": [],
            }
        ),
    )
    monkeypatch.setattr(home_module, "fetch_playlist_metadata", Mock(return_value={"title": "Test Playlist"}))
    monkeypatch.setattr(home_module, "fetch_playlist_items", Mock(return_value=[{"video_id": "v1"}]))
    monkeypatch.setattr(home_module, "create_playlist", Mock())
    monkeypatch.setattr(home_module, "group_videos_by_day", Mock(return_value={}))
    monkeypatch.setattr(home_module, "load_videos", Mock(return_value=[{"date": "2024-01-01T00:00:00Z"}]))
    return None


class DummyUser:
    def __init__(self, data):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)


def test_render_add_playlist_card_renders(mock_ui, mock_utils):
    parent = MagicMock()

    def dummy_refresh():
        pass

    user = User(username="alice", token="tok123", id="id456")
    home_module.render_add_playlist_card(parent, user, dummy_refresh, dummy_refresh)
    assert parent.__enter__.called or parent.__exit__.called or parent.method_calls


def test_render_playlists_list_renders_and_add_card(mock_ui, mock_utils):
    parent = MagicMock()

    def dummy_refresh():
        pass

    user = User(username="alice", token="tok123", id="id456")
    home_module.render_playlists_list(parent, user, dummy_refresh, dummy_refresh)
    assert parent.clear.called


def test_render_dashboard_renders_chart_and_calendar(mock_ui, mock_utils):
    parent = MagicMock()
    home_module.render_dashboard(parent)
    assert parent.clear.called
    assert mock_ui.echart.called
    assert mock_ui.separator.called


def test_render_dashboard_no_videos(mock_ui, monkeypatch):
    parent = MagicMock()
    monkeypatch.setattr(home_module, "load_videos", Mock(return_value=[]))
    home_module.render_dashboard(parent)
    assert parent.clear.called
    assert mock_ui.card.called


def test_with_user_context_logged_in(monkeypatch):
    # Simulate logged-in user
    class DummyStorage:
        pass

    dummy_user = DummyUser({"user": "alice", "token": "tok123", "id": "id456"})
    dummy_storage = DummyStorage()
    dummy_storage.user = dummy_user
    monkeypatch.setattr(home_module.app, "storage", dummy_storage)
    called = {}

    @with_user_context
    def dummy_page(user):
        called["user"] = user

    dummy_page()
    assert vars(called["user"]) == dict(username="alice", token="tok123", id="id456")


def test_with_user_context_not_logged_in(monkeypatch):
    # Simulate not-logged-in user
    class DummyStorage:
        pass

    dummy_user = DummyUser({})
    dummy_storage = DummyStorage()
    dummy_storage.user = dummy_user
    monkeypatch.setattr(home_module.app, "storage", dummy_storage)
    called = {}

    @with_user_context
    def dummy_page(user):
        called["user"] = user

    dummy_page()
    assert called["user"] is None

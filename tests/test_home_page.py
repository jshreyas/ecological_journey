from unittest.mock import MagicMock, Mock

from ui.pages import home as home_module


def test_home_page_connects_state_and_page_components(monkeypatch):
    mock_ui = MagicMock()
    monkeypatch.setattr(home_module, "ui", mock_ui)
    home_state = Mock()
    state_class = Mock(return_value=home_state)
    calendar_tab = Mock()
    feed_tab = Mock()
    playlist_tab = Mock()
    monkeypatch.setattr(home_module, "State", state_class)
    monkeypatch.setattr(home_module, "CalendarTab", Mock(return_value=calendar_tab))
    monkeypatch.setattr(home_module, "FeedTab", Mock(return_value=feed_tab))
    monkeypatch.setattr(home_module, "PlaylistTab", Mock(return_value=playlist_tab))

    home_module.home_page.__wrapped__(None)

    state_class.assert_called_once_with(None)
    calendar_tab.create_tab.assert_called_once()
    playlist_tab.create_tab.assert_called_once()
    feed_tab.create_tab.assert_called_once()
    feed_tab.set_theater_dialog.assert_called_once()
    assert mock_ui.dialog.called
    assert mock_ui.splitter.called

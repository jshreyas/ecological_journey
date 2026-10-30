from unittest.mock import Mock

from ui.pages.components.home import feed_tab as feed_tab_module
from ui.pages.components.home.feed_tab import FeedTab


def create_feed_tab():
    home_state = Mock()
    feed_tab = FeedTab(home_state)
    theater_dialog = Mock()
    player_container = Mock()
    feed_tab.set_theater_dialog(theater_dialog, player_container)
    return feed_tab, theater_dialog, player_container


def test_play_video_inline_opens_theater_without_replacing_feed_post():
    feed_tab, theater_dialog, player_container = create_feed_tab()
    feed_tab.render_player = Mock()
    video = {"video_id": "video-1"}

    feed_tab.play_video_inline(video)

    player_container.clear.assert_called_once_with()
    feed_tab.render_player.assert_called_once_with(video, player_container)
    theater_dialog.open.assert_called_once_with()
    assert feed_tab.active_video_id == "video-1"


def test_selecting_another_video_replaces_theater_player(monkeypatch):
    feed_tab, theater_dialog, player_container = create_feed_tab()
    monkeypatch.setattr(feed_tab_module.ui, "run_javascript", Mock())
    feed_tab.render_player = Mock()
    first_video = {"video_id": "video-1"}
    second_video = {"video_id": "video-2"}

    feed_tab.play_video_inline(first_video)
    feed_tab.play_video_inline(second_video)

    assert player_container.clear.call_count == 2
    assert feed_tab.render_player.call_args_list[0].args == (
        first_video,
        player_container,
    )
    assert feed_tab.render_player.call_args_list[1].args == (
        second_video,
        player_container,
    )
    assert theater_dialog.open.call_count == 2
    assert feed_tab.active_video_id == "video-2"


def test_close_video_dialog_clears_the_player():
    feed_tab, theater_dialog, player_container = create_feed_tab()
    feed_tab.active_video_id = "video-1"

    feed_tab.close_video_dialog()

    theater_dialog.close.assert_called_once_with()
    player_container.clear.assert_called_once_with()
    assert feed_tab.active_video_id is None


def test_set_playback_speed_updates_the_active_player(monkeypatch):
    feed_tab, _, _ = create_feed_tab()
    feed_tab.speed_slider = Mock(value=1.0)
    run_javascript = Mock()
    monkeypatch.setattr(feed_tab_module.ui, "run_javascript", run_javascript)

    feed_tab.set_playback_speed(Mock(value=1.5))

    assert feed_tab.playback_speed == 1.5
    assert feed_tab.speed_slider.value == 1.5
    assert "window.ytConfig.speed = 1.5" in run_javascript.call_args.args[0]
    assert "window.setYTSpeed(1.5)" in run_javascript.call_args.args[0]


def test_open_film_page_navigates_without_deleting_the_dialog_slot(monkeypatch):
    feed_tab, theater_dialog, player_container = create_feed_tab()
    navigate = Mock()
    monkeypatch.setattr(feed_tab_module.ui.navigate, "to", navigate)

    feed_tab.open_film_page("video-1")

    navigate.assert_called_once_with("/film/video-1")
    theater_dialog.close.assert_not_called()
    player_container.clear.assert_not_called()

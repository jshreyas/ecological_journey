from unittest.mock import Mock

from ui.pages.components.film.matadata_tab import MatadataTab


def test_refresh_active_rows_marks_matching_clip_and_anchor():
    video_state = Mock()
    video_state.active_metadata_row_id = "clip-1"
    tab = MatadataTab(video_state, on_play_anchor=None)
    tab.table = Mock()
    tab.table.rows = [
        {"id": "__video_description__", "_is_video_description": True},
        {"id": "anchor-1", "_type": "anchor"},
        {"id": "clip-1", "_type": "clip"},
    ]

    tab._refresh_active_rows()

    assert tab.table.rows == [
        {"id": "__video_description__", "_is_video_description": True},
        {"id": "anchor-1", "_type": "anchor", "_active": False},
        {"id": "clip-1", "_type": "clip", "_active": True},
    ]
    tab.table.update.assert_called_once_with()


def test_refresh_active_rows_does_nothing_without_active_metadata_row():
    video_state = Mock()
    video_state.active_metadata_row_id = None
    tab = MatadataTab(video_state, on_play_anchor=None)
    tab.table = Mock()
    tab.table.rows = [{"id": "clip-1", "_type": "clip"}]

    tab._refresh_active_rows()

    assert tab.table.rows == [{"id": "clip-1", "_type": "clip"}]
    tab.table.update.assert_not_called()

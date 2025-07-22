from unittest.mock import MagicMock

from ui.pages.media_components import render_media_page


def test_render_media_page_renders(monkeypatch):
    # Mock all NiceGUI UI calls
    monkeypatch.setattr("nicegui.ui.label", MagicMock())
    monkeypatch.setattr("nicegui.ui.select", MagicMock())
    monkeypatch.setattr("nicegui.ui.row", MagicMock())
    monkeypatch.setattr("nicegui.ui.column", MagicMock())
    monkeypatch.setattr("nicegui.ui.splitter", MagicMock())
    monkeypatch.setattr("nicegui.ui.input", MagicMock())
    monkeypatch.setattr("nicegui.ui.menu", MagicMock())
    monkeypatch.setattr("nicegui.ui.date", MagicMock())
    monkeypatch.setattr("nicegui.ui.button", MagicMock())
    monkeypatch.setattr("nicegui.ui.chip", MagicMock())
    monkeypatch.setattr("nicegui.ui.grid", MagicMock())
    monkeypatch.setattr("nicegui.ui.card", MagicMock())
    monkeypatch.setattr("nicegui.ui.separator", MagicMock())
    monkeypatch.setattr("nicegui.ui.notify", MagicMock())

    # Provide dummy data loader and functions
    def dummy_loader():
        return [
            {
                "playlist_name": "Test",
                "date": "2024-01-01",
                "labels": ["a"],
                "partners": ["b"],
                "video_id": "vid",
                "clip_id": "cid",
                "title": "Test Title",
                "duration_human": "1:00",
                "clips": [1, 2],
            }
        ]

    render_media_page(
        title="Test",
        data_loader=dummy_loader,
        parse_query_expression=lambda x: lambda y: True,
        navigate_to_film=lambda x, y=None: None,
        show_save_button=True,
        show_clips_count=True,
    )

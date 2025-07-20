"""
Unit tests for ShareDialogTab component
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from ui.pages.film_components.share_dialog_tab import ShareDialogTab
from ui.pages.film_components.video_state import VideoState


class TestShareDialogTab:
    """Test cases for ShareDialogTab component"""

    def setup_method(self):
        """Set up test fixtures"""
        self.video_id = "test_video_123"
        self.mock_video_data = {
            "video_id": "test_video_123",
            "title": "Test Video",
            "partners": ["Alice", "Bob"],
            "labels": ["action", "drama"],
            "clips": [],
        }
        self.video_state = VideoState(self.video_id)
        self.share_dialog_tab = ShareDialogTab(self.video_state)

    @patch("ui.pages.film_components.video_state.load_video")
    def test_init(self, mock_load_video):
        """Test ShareDialogTab initialization"""
        mock_load_video.return_value = self.mock_video_data

        assert self.share_dialog_tab.video_state == self.video_state
        assert self.share_dialog_tab.container is None
        assert self.share_dialog_tab.on_share is None

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.share_dialog_tab.ui")
    def test_create_tab(self, mock_ui, mock_load_video):
        """Test creating the share dialog tab"""
        mock_load_video.return_value = self.mock_video_data
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)

        self.share_dialog_tab.create_tab(mock_container)

        assert self.share_dialog_tab.container == mock_container

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.share_dialog_tab.ui")
    def test_refresh_with_container(self, mock_ui, mock_load_video):
        """Test refreshing the share dialog tab with container"""
        mock_load_video.return_value = self.mock_video_data
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)

        self.share_dialog_tab.container = mock_container
        self.share_dialog_tab.refresh()

        # Should not raise any exceptions
        assert True

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.share_dialog_tab.ui")
    def test_refresh_without_container(self, mock_ui, mock_load_video):
        """Test refreshing the share dialog tab without container"""
        mock_load_video.return_value = self.mock_video_data

        # Should not raise any exceptions
        self.share_dialog_tab.refresh()

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.share_dialog_tab.ui")
    def test_share_clip_without_callback(self, mock_ui, mock_load_video):
        """Test sharing a clip without callback"""
        mock_load_video.return_value = self.mock_video_data
        mock_clip = {"clip_id": "test_clip", "title": "Test Clip"}

        # Should not raise any exceptions
        self.share_dialog_tab.share_clip(mock_clip)

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.share_dialog_tab.ui")
    def test_share_clip_with_callback(self, mock_ui, mock_load_video):
        """Test sharing a clip with callback"""
        mock_load_video.return_value = self.mock_video_data
        mock_clip = {"clip_id": "test_clip", "title": "Test Clip"}
        mock_callback = Mock()
        self.share_dialog_tab.on_share = mock_callback

        self.share_dialog_tab.share_clip(mock_clip)

        mock_callback.assert_called_once_with(mock_clip)

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.share_dialog_tab.ui")
    def test_show_share_dialog(self, mock_ui, mock_load_video):
        """Test showing the share dialog"""
        mock_load_video.return_value = self.mock_video_data
        mock_clip = {"clip_id": "test_clip", "title": "Test Clip"}

        # Mock the dialog and card
        mock_dialog = Mock()
        mock_card = Mock()
        mock_ui.dialog.return_value.__enter__ = Mock(return_value=mock_dialog)
        mock_ui.dialog.return_value.__exit__ = Mock(return_value=None)
        mock_ui.card.return_value.__enter__ = Mock(return_value=mock_card)
        mock_ui.card.return_value.__exit__ = Mock(return_value=None)

        # Should not raise any exceptions
        self.share_dialog_tab._show_share_dialog(mock_clip)

    def test_generate_share_url(self):
        """Test generating share URL"""
        mock_clip = {"clip_id": "test_clip", "video_id": "test_video_123"}

        url = self.share_dialog_tab.generate_share_url(mock_clip)

        # Should contain the video_id and clip_id
        assert "test_video_123" in url
        assert "test_clip" in url

    def test_generate_share_url_without_video_id(self):
        """Test generating share URL when clip doesn't have video_id"""
        mock_clip = {"clip_id": "test_clip"}

        url = self.share_dialog_tab.generate_share_url(mock_clip)

        # Should use the video_state video_id
        assert "test_video_123" in url
        assert "test_clip" in url

    def test_get_base_share_url(self):
        """Test getting base share URL"""
        url = self.share_dialog_tab.get_base_share_url()

        # Should return a string (could be empty if BASE_URL_SHARE is not set)
        assert isinstance(url, str)

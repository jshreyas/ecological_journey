"""
Unit tests for FilmdataTab component
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from ui.pages.film_components.filmdata_tab import FilmdataTab
from ui.pages.film_components.video_state import VideoState


class TestFilmdataTab:
    """Test cases for FilmdataTab component"""

    def setup_method(self):
        """Set up test fixtures"""
        self.video_id = "test_video_123"
        self.mock_video_data = {
            "video_id": "test_video_123",
            "title": "Test Video",
            "partners": ["Alice", "Bob"],
            "labels": ["action", "drama"],
            "notes": "Test notes",
            "clips": [],
        }
        self.video_state = VideoState(self.video_id)
        self.filmdata_tab = FilmdataTab(self.video_state)

    @patch("ui.pages.film_components.video_state.load_video")
    def test_init(self, mock_load_video):
        """Test FilmdataTab initialization"""
        mock_load_video.return_value = self.mock_video_data

        assert self.filmdata_tab.video_state == self.video_state
        assert self.filmdata_tab.container is None
        assert self.filmdata_tab.chips_list == []
        assert self.filmdata_tab.notes_input is None
        assert self.filmdata_tab.on_publish is None

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.filmdata_tab.ui")
    def test_create_tab(self, mock_ui, mock_load_video):
        """Test creating the filmdata tab"""
        mock_load_video.return_value = self.mock_video_data
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)

        self.filmdata_tab.create_tab(mock_container)

        assert self.filmdata_tab.container == mock_container

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.filmdata_tab.ui")
    def test_refresh_with_container(self, mock_ui, mock_load_video):
        """Test refreshing the filmdata tab with container"""
        mock_load_video.return_value = self.mock_video_data
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)

        self.filmdata_tab.container = mock_container
        self.filmdata_tab.refresh()

        # Should clear and recreate the UI
        mock_container.clear.assert_called_once()

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.filmdata_tab.ui")
    def test_refresh_without_container(self, mock_ui, mock_load_video):
        """Test refreshing the filmdata tab without container"""
        mock_load_video.return_value = self.mock_video_data

        # Should not raise any exceptions
        self.filmdata_tab.refresh()

    @patch("ui.pages.film_components.video_state.load_video")
    def test_get_video_data(self, mock_load_video):
        """Test getting video data"""
        mock_load_video.return_value = self.mock_video_data

        video_data = self.filmdata_tab.get_video_data()

        assert video_data == self.mock_video_data

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.filmdata_tab.ui")
    @patch("ui.pages.film_components.filmdata_tab.app")
    def test_handle_save_without_callback(self, mock_app, mock_ui, mock_load_video):
        """Test handle save without custom callback"""
        mock_load_video.return_value = self.mock_video_data
        mock_app.storage.user.get.return_value = "test_token"

        # Mock the save_video_metadata function
        with patch(
            "ui.pages.film_components.filmdata_tab.save_video_metadata"
        ) as mock_save:
            mock_save.return_value = True

            # Set up some test data
            self.filmdata_tab.chips_list = ["@Alice", "#action"]
            self.filmdata_tab.notes_input = Mock()
            self.filmdata_tab.notes_input.value = "Test notes"

            self.filmdata_tab._handle_save()

            # Should call save_video_metadata
            mock_save.assert_called_once()

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.filmdata_tab.ui")
    @patch("ui.pages.film_components.filmdata_tab.app")
    def test_handle_save_failure(self, mock_app, mock_ui, mock_load_video):
        """Test handle save when save fails"""
        mock_load_video.return_value = self.mock_video_data
        mock_app.storage.user.get.return_value = "test_token"

        # Mock the save_video_metadata function to return False
        with patch(
            "ui.pages.film_components.filmdata_tab.save_video_metadata"
        ) as mock_save:
            mock_save.return_value = False

            # Set up some test data
            self.filmdata_tab.chips_list = ["@Alice", "#action"]
            self.filmdata_tab.notes_input = Mock()
            self.filmdata_tab.notes_input.value = "Test notes"

            self.filmdata_tab._handle_save()

            # Should call save_video_metadata
            mock_save.assert_called_once()

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.filmdata_tab.ui")
    @patch("ui.pages.film_components.filmdata_tab.app")
    def test_handle_save_no_token(self, mock_app, mock_ui, mock_load_video):
        """Test handle save when no token is available"""
        mock_load_video.return_value = self.mock_video_data
        mock_app.storage.user.get.return_value = None

        # Should not raise any exceptions
        self.filmdata_tab._handle_save()

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.filmdata_tab.ui")
    @patch("ui.pages.film_components.filmdata_tab.app")
    def test_handle_publish_without_callback(self, mock_app, mock_ui, mock_load_video):
        """Test handle publish without custom callback"""
        mock_load_video.return_value = self.mock_video_data
        mock_app.storage.user.get.return_value = "test_token"

        # Mock the save_video_metadata function
        with patch(
            "ui.pages.film_components.filmdata_tab.save_video_metadata"
        ) as mock_save:
            mock_save.return_value = True

            test_metadata = {"title": "Test", "partners": ["Alice"]}
            self.filmdata_tab.handle_publish(test_metadata)

            # Should call save_video_metadata
            mock_save.assert_called_once()

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.filmdata_tab.ui")
    def test_handle_publish_with_callback(self, mock_ui, mock_load_video):
        """Test handle publish with custom callback"""
        mock_load_video.return_value = self.mock_video_data

        mock_callback = Mock()
        self.filmdata_tab.on_publish = mock_callback

        test_metadata = {"title": "Test", "partners": ["Alice"]}
        self.filmdata_tab.handle_publish(test_metadata)

        # Should call the callback instead of default behavior
        mock_callback.assert_called_once_with(test_metadata)

    @patch("ui.pages.film_components.video_state.load_video")
    def test_reset_fields(self, mock_load_video):
        """Test resetting fields to original values"""
        mock_load_video.return_value = self.mock_video_data

        # Set some modified values
        self.filmdata_tab.chips_list = ["@Charlie", "#comedy"]
        self.filmdata_tab.notes_input = Mock()
        self.filmdata_tab.notes_input.value = "Modified notes"

        self.filmdata_tab._reset_fields()

        # Should reset to original values
        assert self.filmdata_tab.chips_list == ["@Alice", "@Bob", "#action", "#drama"]

    @patch("ui.pages.film_components.video_state.load_video")
    def test_create_chips_input(self, mock_load_video):
        """Test creating chips input"""
        mock_load_video.return_value = self.mock_video_data

        input_ref, chips_list, error_label, container = (
            self.filmdata_tab._create_chips_input(["@Alice", "#action"])
        )

        assert len(chips_list) == 2
        assert "@Alice" in chips_list
        assert "#action" in chips_list
        assert input_ref is not None
        assert error_label is not None
        assert container is not None

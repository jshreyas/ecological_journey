"""
Unit tests for NavigationTab component
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from ui.pages.film_components.navigation_tab import NavigationTab
from ui.pages.film_components.video_state import VideoState


class TestNavigationTab:
    """Test cases for NavigationTab component"""

    def setup_method(self):
        """Set up test fixtures"""
        self.video_id = "test_video_123"
        self.mock_video_data = {
            "video_id": "test_video_123",
            "title": "Test Video",
            "date": "2024-01-15T10:00:00Z",
            "partners": ["Alice", "Bob"],
            "labels": ["action", "drama"],
            "clips": [],
        }
        self.video_state = VideoState(self.video_id)
        self.navigation_tab = NavigationTab(self.video_state)

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.navigation_tab.load_videos")
    def test_init(self, mock_load_videos, mock_load_video):
        """Test NavigationTab initialization"""
        mock_load_video.return_value = self.mock_video_data
        mock_load_videos.return_value = []

        assert self.navigation_tab.video_state == self.video_state
        assert self.navigation_tab.container is None
        assert self.navigation_tab.on_video_select is None
        assert self.navigation_tab.prev_video is None
        assert self.navigation_tab.next_video is None

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.navigation_tab.load_videos")
    @patch("ui.pages.film_components.navigation_tab.ui")
    def test_create_tab(self, mock_ui, mock_load_videos, mock_load_video):
        """Test creating the navigation tab"""
        mock_load_video.return_value = self.mock_video_data
        mock_load_videos.return_value = []
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)

        self.navigation_tab.create_tab(mock_container)

        assert self.navigation_tab.container == mock_container

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.navigation_tab.load_videos")
    @patch("ui.pages.film_components.navigation_tab.ui")
    def test_refresh_with_container(self, mock_ui, mock_load_videos, mock_load_video):
        """Test refreshing the navigation tab with container"""
        mock_load_video.return_value = self.mock_video_data
        mock_load_videos.return_value = []
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)

        self.navigation_tab.container = mock_container
        self.navigation_tab.refresh()

        # Should clear and recreate the UI
        mock_container.clear.assert_called_once()

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.navigation_tab.load_videos")
    @patch("ui.pages.film_components.navigation_tab.ui")
    def test_refresh_without_container(
        self, mock_ui, mock_load_videos, mock_load_video
    ):
        """Test refreshing the navigation tab without container"""
        mock_load_video.return_value = self.mock_video_data
        mock_load_videos.return_value = []

        # Should not raise any exceptions
        self.navigation_tab.refresh()

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.navigation_tab.load_videos")
    def test_find_adjacent_videos(self, mock_load_videos, mock_load_video):
        """Test finding adjacent videos"""
        mock_load_video.return_value = self.mock_video_data

        # Mock sorted videos
        sorted_videos = [
            {"video_id": "prev_video", "date": "2024-01-14T10:00:00Z"},
            {"video_id": "test_video_123", "date": "2024-01-15T10:00:00Z"},
            {"video_id": "next_video", "date": "2024-01-16T10:00:00Z"},
        ]
        mock_load_videos.return_value = sorted_videos

        self.navigation_tab._find_adjacent_videos()

        assert self.navigation_tab.prev_video["video_id"] == "prev_video"
        assert self.navigation_tab.next_video["video_id"] == "next_video"

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.navigation_tab.load_videos")
    def test_find_adjacent_videos_no_adjacent(self, mock_load_videos, mock_load_video):
        """Test finding adjacent videos when none exist"""
        mock_load_video.return_value = self.mock_video_data

        # Mock only current video
        sorted_videos = [{"video_id": "test_video_123", "date": "2024-01-15T10:00:00Z"}]
        mock_load_videos.return_value = sorted_videos

        self.navigation_tab._find_adjacent_videos()

        assert self.navigation_tab.prev_video is None
        assert self.navigation_tab.next_video is None

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.navigation_tab.load_videos")
    def test_find_adjacent_videos_no_date(self, mock_load_videos, mock_load_video):
        """Test finding adjacent videos when video has no date"""
        mock_video_no_date = self.mock_video_data.copy()
        mock_video_no_date["date"] = ""
        mock_load_video.return_value = mock_video_no_date

        self.navigation_tab._find_adjacent_videos()

        assert self.navigation_tab.prev_video is None
        assert self.navigation_tab.next_video is None

    def test_get_adjacent_videos(self):
        """Test getting adjacent videos"""
        self.navigation_tab.prev_video = {"video_id": "prev_video"}
        self.navigation_tab.next_video = {"video_id": "next_video"}

        prev, next_video = self.navigation_tab.get_adjacent_videos()

        assert prev["video_id"] == "prev_video"
        assert next_video["video_id"] == "next_video"

    @patch("ui.pages.film_components.video_state.load_video")
    def test_get_current_video_title(self, mock_load_video):
        """Test getting current video title"""
        mock_load_video.return_value = self.mock_video_data

        title = self.navigation_tab.get_current_video_title()

        assert title == "Test Video"

    @patch("ui.pages.film_components.video_state.load_video")
    def test_get_current_video_title_no_video(self, mock_load_video):
        """Test getting current video title when no video is available"""
        mock_load_video.return_value = None

        title = self.navigation_tab.get_current_video_title()

        assert title == "Untitled Video"

    def test_handle_video_click(self):
        """Test handling video click"""
        mock_video_id = "test_video_456"
        mock_callback = Mock()
        self.navigation_tab.on_video_select = mock_callback

        self.navigation_tab._handle_video_click(mock_video_id)

        mock_callback.assert_called_once_with(mock_video_id)

    @patch("ui.pages.film_components.navigation_tab.navigate_to_film")
    def test_handle_video_click_without_callback(self, mock_navigate):
        """Test handling video click without callback (should navigate)"""
        mock_video_id = "test_video_456"

        self.navigation_tab._handle_video_click(mock_video_id)

        mock_navigate.assert_called_once_with(mock_video_id)

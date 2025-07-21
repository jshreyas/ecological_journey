"""
Unit tests for FilmboardTab component
"""

from unittest.mock import Mock, patch

from ui.pages.film_components.filmboard_tab import FilmboardTab
from ui.pages.film_components.video_state import VideoState


class TestFilmboardTab:
    """Test cases for FilmboardTab component"""

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
        self.filmboard_tab = FilmboardTab(self.video_state)

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.filmboard_tab.load_videos")
    def test_init(self, mock_load_videos, mock_load_video):
        """Test FilmboardTab initialization"""
        mock_load_video.return_value = self.mock_video_data
        mock_load_videos.return_value = []

        assert self.filmboard_tab.video_state == self.video_state
        assert self.filmboard_tab.container is None
        assert self.filmboard_tab.on_video_select is None

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.filmboard_tab.load_videos")
    @patch("ui.pages.film_components.filmboard_tab.ui")
    def test_create_tab(self, mock_ui, mock_load_videos, mock_load_video):
        """Test creating the filmboard tab"""
        mock_load_video.return_value = self.mock_video_data
        mock_load_videos.return_value = []
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)

        self.filmboard_tab.create_tab(mock_container)

        assert self.filmboard_tab.container == mock_container

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.filmboard_tab.load_videos")
    @patch("ui.pages.film_components.filmboard_tab.ui")
    def test_refresh_with_container(self, mock_ui, mock_load_videos, mock_load_video):
        """Test refreshing the filmboard tab with container"""
        mock_load_video.return_value = self.mock_video_data
        mock_load_videos.return_value = []
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)

        self.filmboard_tab.container = mock_container
        self.filmboard_tab.refresh()

        # Should clear and recreate the UI
        mock_container.clear.assert_called_once()

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.filmboard_tab.load_videos")
    @patch("ui.pages.film_components.filmboard_tab.ui")
    def test_refresh_without_container(
        self, mock_ui, mock_load_videos, mock_load_video
    ):
        """Test refreshing the filmboard tab without container"""
        mock_load_video.return_value = self.mock_video_data
        mock_load_videos.return_value = []

        # Should not raise any exceptions
        self.filmboard_tab.refresh()

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.filmboard_tab.load_videos")
    @patch("ui.pages.film_components.filmboard_tab.ui")
    def test_refresh_with_same_day_videos(
        self, mock_ui, mock_load_videos, mock_load_video
    ):
        """Test refresh with videos from the same day"""
        mock_load_video.return_value = self.mock_video_data

        # Mock videos from the same day
        same_day_videos = [
            {
                "video_id": "other_video_456",
                "title": "Other Video",
                "date": "2024-01-15T12:00:00Z",
                "duration_human": "1:30:00",
                "playlist_name": "Test Playlist",
                "clips": [],
                "partners": ["Charlie"],
                "labels": ["comedy"],
            }
        ]
        mock_load_videos.return_value = same_day_videos

        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)
        self.filmboard_tab.container = mock_container
        self.filmboard_tab.refresh()

        # Should clear and recreate the UI
        mock_container.clear.assert_called_once()

    @patch("ui.pages.film_components.video_state.load_video")
    def test_get_same_day_videos_count(self, mock_load_video):
        """Test getting count of videos from the same day"""
        mock_load_video.return_value = self.mock_video_data

        with patch(
            "ui.pages.film_components.filmboard_tab.load_videos"
        ) as mock_load_videos:
            same_day_videos = [
                {"video_id": "other1", "date": "2024-01-15T12:00:00Z"},
                {"video_id": "other2", "date": "2024-01-15T14:00:00Z"},
            ]
            mock_load_videos.return_value = same_day_videos

            count = self.filmboard_tab.get_same_day_videos_count()

            assert count == 2

    @patch("ui.pages.film_components.video_state.load_video")
    def test_get_current_video_date(self, mock_load_video):
        """Test getting current video date"""
        mock_load_video.return_value = self.mock_video_data

        date = self.filmboard_tab.get_current_video_date()

        assert date == "2024-01-15"

    @patch("ui.pages.film_components.video_state.load_video")
    def test_get_current_video_date_no_date(self, mock_load_video):
        """Test getting current video date when no date is available"""
        mock_video_no_date = self.mock_video_data.copy()
        mock_video_no_date["date"] = ""
        mock_load_video.return_value = mock_video_no_date

        date = self.filmboard_tab.get_current_video_date()

        assert date == ""

    @patch("ui.pages.film_components.video_state.load_video")
    def test_get_current_video_date_no_video(self, mock_load_video):
        """Test getting current video date when no video is available"""
        mock_load_video.return_value = None

        date = self.filmboard_tab.get_current_video_date()

        assert date == ""

    def test_handle_video_click(self):
        """Test handling video click"""
        mock_video_id = "test_video_456"
        mock_callback = Mock()
        self.filmboard_tab.on_video_select = mock_callback

        self.filmboard_tab._handle_video_click(mock_video_id)

        mock_callback.assert_called_once_with(mock_video_id)

    @patch("ui.pages.film_components.filmboard_tab.navigate_to_film")
    def test_handle_video_click_without_callback(self, mock_navigate):
        """Test handling video click without callback (should navigate)"""
        mock_video_id = "test_video_456"

        self.filmboard_tab._handle_video_click(mock_video_id)

        mock_navigate.assert_called_once_with(mock_video_id)

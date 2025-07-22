"""
Unit tests for VideoState component
"""

from unittest.mock import Mock, patch

from ui.pages.components.film.video_state import VideoState


class TestVideoState:
    """Test cases for VideoState class"""

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

    @patch("ui.pages.components.film.video_state.load_video")
    def test_init(self, mock_load_video):
        """Test VideoState initialization"""
        mock_load_video.return_value = self.mock_video_data

        video_state = VideoState(self.video_id)

        assert video_state.video_id == self.video_id
        assert video_state._refresh_callbacks == []
        assert video_state._video_data is None  # Should start as None

    @patch("ui.pages.components.film.video_state.load_video")
    def test_get_video(self, mock_load_video):
        """Test getting video data"""
        mock_load_video.return_value = self.mock_video_data

        video_state = VideoState(self.video_id)
        video_data = video_state.get_video()

        assert video_data == self.mock_video_data
        mock_load_video.assert_called_once_with(self.video_id)

    @patch("ui.pages.components.film.video_state.load_video")
    def test_get_video_cached(self, mock_load_video):
        """Test getting video data from cache"""
        mock_load_video.return_value = self.mock_video_data

        video_state = VideoState(self.video_id)

        # First call should load from API
        video_data1 = video_state.get_video()
        # Second call should use cached data
        video_data2 = video_state.get_video()

        assert video_data1 == video_data2 == self.mock_video_data
        # Should only call load_video once due to caching
        mock_load_video.assert_called_once_with(self.video_id)

    @patch("ui.pages.components.film.video_state.load_video")
    def test_refresh(self, mock_load_video):
        """Test refreshing video data"""
        mock_load_video.return_value = self.mock_video_data

        video_state = VideoState(self.video_id)

        # Add a mock callback
        mock_callback = Mock()
        video_state.add_refresh_callback(mock_callback)

        # Refresh should clear cache and call callbacks
        video_state.refresh()

        # Should call load_video again
        assert mock_load_video.call_count == 1  # Once in refresh
        # Should call the callback
        mock_callback.assert_called_once()

    @patch("ui.pages.components.film.video_state.load_video")
    def test_add_refresh_callback(self, mock_load_video):
        """Test adding refresh callbacks"""
        mock_load_video.return_value = self.mock_video_data

        video_state = VideoState(self.video_id)

        mock_callback1 = Mock()
        mock_callback2 = Mock()

        video_state.add_refresh_callback(mock_callback1)
        video_state.add_refresh_callback(mock_callback2)

        assert len(video_state._refresh_callbacks) == 2
        assert mock_callback1 in video_state._refresh_callbacks
        assert mock_callback2 in video_state._refresh_callbacks

    @patch("ui.pages.components.film.video_state.load_video")
    def test_remove_refresh_callback(self, mock_load_video):
        """Test removing refresh callbacks"""
        mock_load_video.return_value = self.mock_video_data

        video_state = VideoState(self.video_id)

        mock_callback = Mock()
        video_state.add_refresh_callback(mock_callback)

        assert len(video_state._refresh_callbacks) == 1

        video_state.remove_refresh_callback(mock_callback)

        assert len(video_state._refresh_callbacks) == 0
        assert mock_callback not in video_state._refresh_callbacks

    @patch("ui.pages.components.film.video_state.load_video")
    def test_refresh_with_multiple_callbacks(self, mock_load_video):
        """Test refresh with multiple callbacks"""
        mock_load_video.return_value = self.mock_video_data

        video_state = VideoState(self.video_id)

        mock_callback1 = Mock()
        mock_callback2 = Mock()
        mock_callback3 = Mock()

        video_state.add_refresh_callback(mock_callback1)
        video_state.add_refresh_callback(mock_callback2)
        video_state.add_refresh_callback(mock_callback3)

        video_state.refresh()

        # All callbacks should be called
        mock_callback1.assert_called_once()
        mock_callback2.assert_called_once()
        mock_callback3.assert_called_once()

    @patch("ui.pages.components.film.video_state.load_video")
    def test_get_video_no_data(self, mock_load_video):
        """Test getting video when no data is available"""
        mock_load_video.return_value = None

        video_state = VideoState(self.video_id)
        video_data = video_state.get_video()

        assert video_data is None

    @patch("ui.pages.components.film.video_state.load_video")
    def test_refresh_clears_cache(self, mock_load_video):
        """Test that refresh clears the cache"""
        mock_load_video.return_value = self.mock_video_data

        video_state = VideoState(self.video_id)

        # Get video data (should cache it)
        video_state.get_video()

        # Change the mock to return different data
        updated_video_data = self.mock_video_data.copy()
        updated_video_data["title"] = "Updated Title"
        mock_load_video.return_value = updated_video_data

        # Refresh should clear cache and load new data
        video_state.refresh()

        # Get video data again
        video_data = video_state.get_video()

        # Should return the updated data
        assert video_data["title"] == "Updated Title"

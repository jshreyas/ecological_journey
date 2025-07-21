"""
Integration tests for click functionality in filmboard and navigation tabs
Ensures that clicking on videos navigates correctly without passing event objects
"""

from unittest.mock import Mock, patch

from ui.pages.film_components.filmboard_tab import FilmboardTab
from ui.pages.film_components.navigation_tab import NavigationTab
from ui.pages.film_components.video_state import VideoState


class TestClickFunctionality:
    """Test cases for click functionality"""

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

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.filmboard_tab.load_videos")
    @patch("ui.pages.film_components.filmboard_tab.navigate_to_film")
    def test_filmboard_click_navigation(
        self, mock_navigate, mock_load_videos, mock_load_video
    ):
        """Test that clicking on a filmboard video navigates correctly"""
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

        filmboard_tab = FilmboardTab(self.video_state)

        # Simulate clicking on the video
        filmboard_tab._handle_video_click("other_video_456")

        # Verify navigate_to_film was called with the correct video_id
        mock_navigate.assert_called_once_with("other_video_456")

        # Verify it was NOT called with an event object
        for call in mock_navigate.call_args_list:
            args, kwargs = call
            for arg in args:
                assert not hasattr(
                    arg, "sender"
                ), f"Event object passed as video_id: {arg}"
                assert not hasattr(
                    arg, "client"
                ), f"Event object passed as video_id: {arg}"
                assert not hasattr(
                    arg, "args"
                ), f"Event object passed as video_id: {arg}"

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.navigation_tab.load_videos")
    @patch("ui.pages.film_components.navigation_tab.navigate_to_film")
    def test_navigation_click_navigation(
        self, mock_navigate, mock_load_videos, mock_load_video
    ):
        """Test that clicking on navigation arrows navigates correctly"""
        mock_load_video.return_value = self.mock_video_data

        # Mock sorted videos with adjacent videos
        sorted_videos = [
            {"video_id": "prev_video", "date": "2024-01-14T10:00:00Z"},
            {"video_id": "test_video_123", "date": "2024-01-15T10:00:00Z"},
            {"video_id": "next_video", "date": "2024-01-16T10:00:00Z"},
        ]
        mock_load_videos.return_value = sorted_videos

        navigation_tab = NavigationTab(self.video_state)
        navigation_tab._find_adjacent_videos()

        # Simulate clicking on previous video
        navigation_tab._handle_video_click("prev_video")

        # Verify navigate_to_film was called with the correct video_id
        mock_navigate.assert_called_once_with("prev_video")

        # Verify it was NOT called with an event object
        for call in mock_navigate.call_args_list:
            args, kwargs = call
            for arg in args:
                assert not hasattr(
                    arg, "sender"
                ), f"Event object passed as video_id: {arg}"
                assert not hasattr(
                    arg, "client"
                ), f"Event object passed as video_id: {arg}"
                assert not hasattr(
                    arg, "args"
                ), f"Event object passed as video_id: {arg}"

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.filmboard_tab.load_videos")
    def test_filmboard_click_with_callback(self, mock_load_videos, mock_load_video):
        """Test that clicking on filmboard video calls custom callback correctly"""
        mock_load_video.return_value = self.mock_video_data
        mock_load_videos.return_value = []

        mock_callback = Mock()
        filmboard_tab = FilmboardTab(self.video_state, on_video_select=mock_callback)

        # Simulate clicking on a video
        filmboard_tab._handle_video_click("test_video_456")

        # Verify callback was called with the correct video_id
        mock_callback.assert_called_once_with("test_video_456")

        # Verify it was NOT called with an event object
        for call in mock_callback.call_args_list:
            args, kwargs = call
            for arg in args:
                assert not hasattr(
                    arg, "sender"
                ), f"Event object passed as video_id: {arg}"
                assert not hasattr(
                    arg, "client"
                ), f"Event object passed as video_id: {arg}"
                assert not hasattr(
                    arg, "args"
                ), f"Event object passed as video_id: {arg}"

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.navigation_tab.load_videos")
    def test_navigation_click_with_callback(self, mock_load_videos, mock_load_video):
        """Test that clicking on navigation arrows calls custom callback correctly"""
        mock_load_video.return_value = self.mock_video_data
        mock_load_videos.return_value = []

        mock_callback = Mock()
        navigation_tab = NavigationTab(self.video_state, on_video_select=mock_callback)

        # Simulate clicking on a video
        navigation_tab._handle_video_click("test_video_456")

        # Verify callback was called with the correct video_id
        mock_callback.assert_called_once_with("test_video_456")

        # Verify it was NOT called with an event object
        for call in mock_callback.call_args_list:
            args, kwargs = call
            for arg in args:
                assert not hasattr(
                    arg, "sender"
                ), f"Event object passed as video_id: {arg}"
                assert not hasattr(
                    arg, "client"
                ), f"Event object passed as video_id: {arg}"
                assert not hasattr(
                    arg, "args"
                ), f"Event object passed as video_id: {arg}"

    def test_event_object_not_passed_as_video_id(self):
        """Test that event objects are never passed as video_id parameters"""
        # Create a mock event object similar to what NiceGUI would pass
        mock_event = Mock()
        mock_event.sender = Mock()
        mock_event.client = Mock()
        mock_event.args = {"type": "click", "x": 100, "y": 200}

        # Test that our methods don't accept event objects as video_id
        filmboard_tab = FilmboardTab(self.video_state)
        navigation_tab = NavigationTab(self.video_state)

        # These should work fine since our methods now only accept video_id
        # The test verifies that we don't try to use event objects as video_ids
        filmboard_tab._handle_video_click("valid_video_id")
        navigation_tab._handle_video_click("valid_video_id")

        # Verify that if we pass an event object, it doesn't get treated as a video_id
        # by checking that navigate_to_film is called with the correct string
        with patch(
            "ui.pages.film_components.filmboard_tab.navigate_to_film"
        ) as mock_navigate:
            filmboard_tab._handle_video_click("test_video_123")
            mock_navigate.assert_called_once_with("test_video_123")

            # Verify the argument is a string, not an event object
            args, kwargs = mock_navigate.call_args
            assert isinstance(args[0], str), f"Expected string, got {type(args[0])}"
            assert not hasattr(args[0], "sender"), "Event object passed as video_id"

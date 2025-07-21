"""
Unit tests for ClipperTab component
"""

from unittest.mock import Mock, patch

from ui.pages.film_components.clipper_tab import ClipperTab
from ui.pages.film_components.video_state import VideoState


class TestClipperTab:
    """Test cases for ClipperTab component"""

    def setup_method(self):
        """Set up test fixtures"""
        self.video_id = "test_video_123"
        self.mock_video_data = {
            "video_id": "test_video_123",
            "title": "Test Video",
            "duration_seconds": 3600,
            "partners": ["Alice", "Bob"],
            "labels": ["action", "drama"],
            "clips": [
                {
                    "clip_id": "clip1",
                    "title": "Test Clip 1",
                    "start": 0,
                    "end": 60,
                    "speed": 1.0,
                    "description": "Test description",
                    "partners": ["Alice"],
                    "labels": ["action"],
                }
            ],
        }
        self.video_state = VideoState(self.video_id)
        self.clipper_tab = ClipperTab(self.video_state)

    @patch("ui.pages.film_components.video_state.load_video")
    def test_init(self, mock_load_video):
        """Test ClipperTab initialization"""
        mock_load_video.return_value = self.mock_video_data

        assert self.clipper_tab.video_state == self.video_state
        assert self.clipper_tab.container is None
        assert self.clipper_tab.on_edit_clip is None

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.clipper_tab.ui")
    def test_create_tab(self, mock_ui, mock_load_video):
        """Test creating the clipper tab"""
        mock_load_video.return_value = self.mock_video_data
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)

        self.clipper_tab.create_tab(mock_container)

        assert self.clipper_tab.container == mock_container

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.clipper_tab.ui")
    def test_refresh_with_container(self, mock_ui, mock_load_video):
        """Test refreshing the clipper tab with container"""
        mock_load_video.return_value = self.mock_video_data
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)

        self.clipper_tab.container = mock_container
        self.clipper_tab.refresh()

        # Should clear and recreate the UI
        mock_container.clear.assert_called_once()

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.clipper_tab.ui")
    def test_refresh_without_container(self, mock_ui, mock_load_video):
        """Test refreshing the clipper tab without container"""
        mock_load_video.return_value = self.mock_video_data

        # Should not raise any exceptions
        self.clipper_tab.refresh()

    @patch("ui.pages.film_components.video_state.load_video")
    def test_get_video_data(self, mock_load_video):
        """Test getting video data"""
        mock_load_video.return_value = self.mock_video_data

        video_data = self.clipper_tab.get_video_data()

        assert video_data == self.mock_video_data

    @patch("ui.pages.film_components.video_state.load_video")
    def test_get_clips(self, mock_load_video):
        """Test getting clips from video data"""
        mock_load_video.return_value = self.mock_video_data

        clips = self.clipper_tab.get_clips()

        assert clips == self.mock_video_data["clips"]

    @patch("ui.pages.film_components.video_state.load_video")
    def test_get_clips_no_video(self, mock_load_video):
        """Test getting clips when no video data is available"""
        mock_load_video.return_value = None

        clips = self.clipper_tab.get_clips()

        assert clips == []

    def test_play_clip(self):
        """Test playing a clip"""
        mock_clip = {"clip_id": "test_clip", "title": "Test Clip"}

        # Should not raise any exceptions
        self.clipper_tab._play_clip(mock_clip)

    @patch("ui.pages.film_components.video_state.load_video")
    def test_format_time(self, mock_load_video):
        """Test time formatting"""
        mock_load_video.return_value = self.mock_video_data

        # Test various time formats
        assert self.clipper_tab._format_time(0) == "00:00"
        assert self.clipper_tab._format_time(30) == "00:30"
        assert self.clipper_tab._format_time(60) == "01:00"
        assert self.clipper_tab._format_time(90) == "01:30"
        assert self.clipper_tab._format_time(3600) == "01:00:00"

    @patch("ui.pages.film_components.video_state.load_video")
    def test_create_chips_input(self, mock_load_video):
        """Test creating chips input"""
        mock_load_video.return_value = self.mock_video_data

        input_ref, chips_list, error_label, container = (
            self.clipper_tab._create_chips_input(["@Alice", "#action"])
        )

        assert len(chips_list) == 2
        assert "@Alice" in chips_list
        assert "#action" in chips_list
        assert input_ref is not None
        assert error_label is not None
        assert container is not None

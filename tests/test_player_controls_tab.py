"""
Unit tests for PlayerControlsTab component
"""

from unittest.mock import Mock, patch

from ui.pages.film_components.player_controls_tab import PlayerControlsTab
from ui.pages.film_components.video_state import VideoState


class TestPlayerControlsTab:
    """Test cases for PlayerControlsTab component"""

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
        self.player_controls_tab = PlayerControlsTab(self.video_state)

    @patch("ui.pages.film_components.video_state.load_video")
    def test_init(self, mock_load_video):
        """Test PlayerControlsTab initialization"""
        mock_load_video.return_value = self.mock_video_data

        assert self.player_controls_tab.video_state == self.video_state
        assert self.player_controls_tab.container is None
        assert self.player_controls_tab.on_clip_play is None
        assert self.player_controls_tab.player_speed["value"] == 1.0

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.player_controls_tab.ui")
    @patch("ui.pages.film_components.player_controls_tab.VideoPlayer")
    def test_create_tab(self, mock_video_player, mock_ui, mock_load_video):
        """Test creating the player controls tab"""
        mock_load_video.return_value = self.mock_video_data
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)

        self.player_controls_tab.create_tab(mock_container)

        assert self.player_controls_tab.container == mock_container

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.player_controls_tab.ui")
    @patch("ui.pages.film_components.player_controls_tab.VideoPlayer")
    def test_create_tab_normal_mode(self, mock_video_player, mock_ui, mock_load_video):
        """Test creating the player controls tab in normal mode"""
        mock_load_video.return_value = self.mock_video_data
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)

        self.player_controls_tab.create_tab(mock_container, play_clips_playlist=False)

        assert self.player_controls_tab.container == mock_container

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.player_controls_tab.ui")
    @patch("ui.pages.film_components.player_controls_tab.VideoPlayer")
    @patch("ui.pages.film_components.player_controls_tab.load_video")
    def test_create_tab_playlist_mode(
        self, mock_load_video_func, mock_video_player, mock_ui, mock_load_video
    ):
        """Test creating the player controls tab in playlist mode"""
        mock_load_video.return_value = self.mock_video_data
        mock_load_video_func.return_value = self.mock_video_data
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)

        self.player_controls_tab.create_tab(mock_container, play_clips_playlist=True)

        assert self.player_controls_tab.container == mock_container

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.player_controls_tab.ui")
    @patch("ui.pages.film_components.player_controls_tab.VideoPlayer")
    def test_create_tab_autoplay_clip(
        self, mock_video_player, mock_ui, mock_load_video
    ):
        """Test creating the player controls tab with autoplay clip"""
        mock_load_video.return_value = self.mock_video_data
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)
        mock_clip = {"clip_id": "test_clip", "title": "Test Clip"}

        self.player_controls_tab.create_tab(mock_container, autoplay_clip=mock_clip)

        assert self.player_controls_tab.container == mock_container

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.player_controls_tab.ui")
    @patch("ui.pages.film_components.player_controls_tab.VideoPlayer")
    def test_refresh_with_container(self, mock_video_player, mock_ui, mock_load_video):
        """Test refreshing the player controls tab with container"""
        mock_load_video.return_value = self.mock_video_data
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)

        self.player_controls_tab.container = mock_container
        self.player_controls_tab.refresh()

        # Should clear and recreate the UI
        mock_container.clear.assert_called_once()

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.player_controls_tab.ui")
    def test_refresh_without_container(self, mock_ui, mock_load_video):
        """Test refreshing the player controls tab without container"""
        mock_load_video.return_value = self.mock_video_data

        # Should not raise any exceptions
        self.player_controls_tab.refresh()

    def test_play_clip_without_callback(self):
        """Test playing a clip without callback"""
        mock_clip = {"clip_id": "test_clip", "title": "Test Clip"}

        # Should not raise any exceptions
        self.player_controls_tab.play_clip(mock_clip)

    def test_play_clip_with_callback(self):
        """Test playing a clip with callback"""
        mock_clip = {"clip_id": "test_clip", "title": "Test Clip"}
        mock_callback = Mock()
        self.player_controls_tab.on_clip_play = mock_callback

        self.player_controls_tab.play_clip(mock_clip)

        mock_callback.assert_called_once_with(mock_clip)

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.player_controls_tab.ui")
    @patch("ui.pages.film_components.player_controls_tab.load_video")
    def test_play_clips_playlist_mode_with_clips(
        self, mock_load_video_func, mock_ui, mock_load_video
    ):
        """Test playing clips in playlist mode with clips available"""
        mock_load_video.return_value = self.mock_video_data
        mock_load_video_func.return_value = self.mock_video_data
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)

        self.player_controls_tab.container = mock_container
        self.player_controls_tab.play_clips_playlist_mode()

        # Should not raise any exceptions
        assert True

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.player_controls_tab.ui")
    @patch("ui.pages.film_components.player_controls_tab.load_video")
    def test_play_clips_playlist_mode_no_clips(
        self, mock_load_video_func, mock_ui, mock_load_video
    ):
        """Test playing clips in playlist mode with no clips"""
        mock_video_no_clips = self.mock_video_data.copy()
        mock_video_no_clips["clips"] = []
        mock_load_video.return_value = mock_video_no_clips
        mock_load_video_func.return_value = mock_video_no_clips
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)

        self.player_controls_tab.container = mock_container
        self.player_controls_tab.play_clips_playlist_mode()

        # Should not raise any exceptions
        assert True

    def test_play_next_clip(self):
        """Test playing the next clip in playlist"""
        # Set up playlist state
        self.player_controls_tab.clips_playlist_state["clips"] = [
            {"clip_id": "clip1", "title": "Clip 1"},
            {"clip_id": "clip2", "title": "Clip 2"},
        ]
        self.player_controls_tab.clips_playlist_state["index"] = 0

        # Should not raise any exceptions
        self.player_controls_tab._play_next_clip()

    def test_set_player_speed(self):
        """Test setting player speed"""
        self.player_controls_tab.set_player_speed(1.5)

        assert self.player_controls_tab.get_player_speed() == 1.5

    def test_get_player_speed(self):
        """Test getting player speed"""
        self.player_controls_tab.player_speed["value"] = 2.0

        assert self.player_controls_tab.get_player_speed() == 2.0

    def test_get_player_container(self):
        """Test getting player container"""
        mock_container = Mock()
        self.player_controls_tab.player_container["ref"] = mock_container

        assert self.player_controls_tab.get_player_container() == mock_container

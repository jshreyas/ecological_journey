"""
Integration tests for tab components working together
"""

from unittest.mock import Mock, patch

from ui.pages.components.film.metaforge_tab import MetaforgeTab
from ui.pages.components.film.share_dialog_tab import ShareDialogTab
from ui.pages.components.film.video_state import VideoState


class TestComponentsIntegration:
    """Test that components work together properly"""

    def setup_method(self):
        """Set up test fixtures"""
        self.video_id = "test_video_123"
        self.mock_video_data = {
            "video_id": "test_video_123",
            "title": "Test Video",
            "partners": ["Alice", "Bob"],
            "labels": ["action", "drama"],
            "notes": "Test notes",
            "clips": [
                {
                    "clip_id": "clip1",
                    "title": "Test Clip",
                    "start": 0,
                    "end": 60,
                    "speed": 1.0,
                    "description": "Test clip description",
                    "labels": ["action"],
                    "partners": ["Alice"],
                }
            ],
        }
        self.video_state = VideoState(self.video_id)

    @patch("ui.pages.components.film.video_state.load_video")
    @patch("ui.pages.components.film.filmboard_tab.load_videos")
    def test_components_share_video_state(self, mock_load_videos, mock_load_video):
        """Test that all components share the same video state"""
        mock_load_video.return_value = self.mock_video_data
        mock_load_videos.return_value = [self.mock_video_data]

        # Create components
        metaforge_tab = MetaforgeTab(self.video_state)
        share_dialog_tab = ShareDialogTab(self.video_state)

        # Verify all components use the same video state
        assert metaforge_tab.video_state == self.video_state
        assert share_dialog_tab.video_state == self.video_state

    @patch("ui.pages.components.film.video_state.load_video")
    @patch("ui.pages.components.film.filmboard_tab.load_videos")
    def test_components_register_refresh_callbacks(self, mock_load_videos, mock_load_video):
        """Test that components register refresh callbacks with video state"""
        mock_load_video.return_value = self.mock_video_data
        mock_load_videos.return_value = [self.mock_video_data]

        # Create components
        metaforge_tab = MetaforgeTab(self.video_state)
        share_dialog_tab = ShareDialogTab(self.video_state)

        # Verify refresh callbacks are registered (using private attribute)
        # Only components that need to refresh when video state changes register callbacks
        assert len(self.video_state._refresh_callbacks) == 5
        assert metaforge_tab.refresh in self.video_state._refresh_callbacks
        assert share_dialog_tab.refresh in self.video_state._refresh_callbacks

        # These components don't register callbacks as they load data independently
        # filmboard_tab, navigation_tab, player_controls_tab

    @patch("ui.pages.components.film.video_state.load_video")
    @patch("ui.pages.components.film.filmboard_tab.load_videos")
    def test_video_state_refresh_notifies_all_components(self, mock_load_videos, mock_load_video):
        """Test that video state refresh notifies all components"""
        mock_load_video.return_value = self.mock_video_data
        mock_load_videos.return_value = [self.mock_video_data]

        # Create mock refresh methods first
        mock_filmdata_refresh = Mock()
        mock_clipper_refresh = Mock()
        mock_clipboard_refresh = Mock()
        mock_metaforge_refresh = Mock()
        mock_share_dialog_refresh = Mock()

        # Create components and replace their refresh methods
        metaforge_tab = MetaforgeTab(self.video_state)
        share_dialog_tab = ShareDialogTab(self.video_state)

        # Replace the refresh methods with mocks
        metaforge_tab.refresh = mock_metaforge_refresh
        share_dialog_tab.refresh = mock_share_dialog_refresh

        # Update the callbacks in video state to use the mocked methods
        self.video_state._refresh_callbacks.clear()
        self.video_state._refresh_callbacks.extend(
            [
                mock_filmdata_refresh,
                mock_clipper_refresh,
                mock_clipboard_refresh,
                mock_metaforge_refresh,
                mock_share_dialog_refresh,
            ]
        )

        # Trigger refresh
        self.video_state.refresh()

        # Verify all components were notified
        mock_filmdata_refresh.assert_called_once()
        mock_clipper_refresh.assert_called_once()
        mock_clipboard_refresh.assert_called_once()
        mock_metaforge_refresh.assert_called_once()
        mock_share_dialog_refresh.assert_called_once()

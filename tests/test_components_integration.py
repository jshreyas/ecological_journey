"""
Integration tests for tab components working together
"""

from unittest.mock import Mock, patch

from ui.pages.film_components.clipboard_tab import ClipboardTab
from ui.pages.film_components.clipper_tab import ClipperTab
from ui.pages.film_components.filmdata_tab import FilmdataTab
from ui.pages.film_components.metaforge_tab import MetaforgeTab
from ui.pages.film_components.share_dialog_tab import ShareDialogTab
from ui.pages.film_components.video_state import VideoState


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

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.filmboard_tab.load_videos")
    def test_components_share_video_state(self, mock_load_videos, mock_load_video):
        """Test that all components share the same video state"""
        mock_load_video.return_value = self.mock_video_data
        mock_load_videos.return_value = [self.mock_video_data]

        # Create components
        filmdata_tab = FilmdataTab(self.video_state)
        clipper_tab = ClipperTab(self.video_state)
        clipboard_tab = ClipboardTab(self.video_state)
        metaforge_tab = MetaforgeTab(self.video_state)
        share_dialog_tab = ShareDialogTab(self.video_state)

        # Verify all components use the same video state
        assert filmdata_tab.video_state == self.video_state
        assert clipper_tab.video_state == self.video_state
        assert clipboard_tab.video_state == self.video_state
        assert metaforge_tab.video_state == self.video_state
        assert share_dialog_tab.video_state == self.video_state

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.filmboard_tab.load_videos")
    def test_components_register_refresh_callbacks(self, mock_load_videos, mock_load_video):
        """Test that components register refresh callbacks with video state"""
        mock_load_video.return_value = self.mock_video_data
        mock_load_videos.return_value = [self.mock_video_data]

        # Create components
        filmdata_tab = FilmdataTab(self.video_state)
        clipper_tab = ClipperTab(self.video_state)
        clipboard_tab = ClipboardTab(self.video_state)
        metaforge_tab = MetaforgeTab(self.video_state)
        share_dialog_tab = ShareDialogTab(self.video_state)

        # Verify refresh callbacks are registered (using private attribute)
        # Only components that need to refresh when video state changes register callbacks
        assert len(self.video_state._refresh_callbacks) == 5
        assert filmdata_tab.refresh in self.video_state._refresh_callbacks
        assert clipper_tab.refresh in self.video_state._refresh_callbacks
        assert clipboard_tab.refresh in self.video_state._refresh_callbacks
        assert metaforge_tab.refresh in self.video_state._refresh_callbacks
        assert share_dialog_tab.refresh in self.video_state._refresh_callbacks

        # These components don't register callbacks as they load data independently
        # filmboard_tab, navigation_tab, player_controls_tab

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.filmboard_tab.load_videos")
    def test_clipboard_clipper_integration(self, mock_load_videos, mock_load_video):
        """Test that clipboard and clipper tabs can communicate"""
        mock_load_video.return_value = self.mock_video_data
        mock_load_videos.return_value = [self.mock_video_data]

        # Create components with integration
        clipper_tab = ClipperTab(self.video_state)
        clipboard_tab = ClipboardTab(self.video_state, on_edit_clip=clipper_tab.on_edit_clip)

        # Verify the callback is set
        assert clipboard_tab.on_edit_clip == clipper_tab.on_edit_clip

    @patch("ui.pages.film_components.video_state.load_video")
    @patch("ui.pages.film_components.filmboard_tab.load_videos")
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
        filmdata_tab = FilmdataTab(self.video_state)
        clipper_tab = ClipperTab(self.video_state)
        clipboard_tab = ClipboardTab(self.video_state)
        metaforge_tab = MetaforgeTab(self.video_state)
        share_dialog_tab = ShareDialogTab(self.video_state)

        # Replace the refresh methods with mocks
        filmdata_tab.refresh = mock_filmdata_refresh
        clipper_tab.refresh = mock_clipper_refresh
        clipboard_tab.refresh = mock_clipboard_refresh
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

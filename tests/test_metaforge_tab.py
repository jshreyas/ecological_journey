"""
Unit tests for MetaforgeTab component
"""

from unittest.mock import Mock, patch

from ui.pages.components.film.metaforge_tab import MetaforgeTab
from ui.pages.components.film.video_state import VideoState
from ui.utils.user_context import User


class TestMetaforgeTab:
    """Test cases for MetaforgeTab component"""

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
        self.user = User(username="alice", token="tok123", id="id456")
        self.metaforge_tab = MetaforgeTab(self.video_state, self.user)

    @patch("ui.pages.components.film.video_state.load_video")
    def test_init(self, mock_load_video):
        """Test MetaforgeTab initialization"""
        mock_load_video.return_value = self.mock_video_data

        assert self.metaforge_tab.video_state == self.video_state
        assert self.metaforge_tab.container is None
        assert self.metaforge_tab.editor_container["ref"] is None
        assert self.metaforge_tab.on_publish is None

    @patch("ui.pages.components.film.video_state.load_video")
    def test_create_tab(self, mock_load_video):
        """Test creating the metaforge tab"""
        mock_load_video.return_value = self.mock_video_data
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)

        self.metaforge_tab.create_tab(mock_container)

        assert self.metaforge_tab.container == mock_container

    @patch("ui.pages.components.film.video_state.load_video")
    def test_refresh_with_container(self, mock_load_video):
        """Test refreshing the metaforge tab with container"""
        mock_load_video.return_value = self.mock_video_data
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)

        self.metaforge_tab.container = mock_container
        self.metaforge_tab.refresh()

        # Should clear and recreate the UI
        mock_container.clear.assert_called_once()

    @patch("ui.pages.components.film.video_state.load_video")
    def test_refresh_without_container(self, mock_load_video):
        """Test refreshing the metaforge tab without container"""
        mock_load_video.return_value = self.mock_video_data

        # Should not raise any exceptions
        self.metaforge_tab.refresh()

    @patch("ui.pages.components.film.video_state.load_video")
    def test_get_video_data(self, mock_load_video):
        """Test getting video data"""
        mock_load_video.return_value = self.mock_video_data

        video_data = self.metaforge_tab.get_video_data()

        assert video_data == self.mock_video_data

    def test_seconds_to_timestamp(self):
        """Test seconds to timestamp conversion"""
        # Test seconds
        assert self.metaforge_tab._seconds_to_timestamp(30) == "0:30"

        # Test minutes and seconds
        assert self.metaforge_tab._seconds_to_timestamp(90) == "1:30"

        # Test zero
        assert self.metaforge_tab._seconds_to_timestamp(0) == "0:00"

    def test_parse_timestamp(self):
        """Test timestamp parsing"""
        # Test mm:ss format
        assert self.metaforge_tab._parse_timestamp("1:30") == 90

        # Test hh:mm:ss format
        assert self.metaforge_tab._parse_timestamp("1:01:01") == 3661

        # Test seconds only
        assert self.metaforge_tab._parse_timestamp("30") == 30

        # Test numeric input
        assert self.metaforge_tab._parse_timestamp(90) == 90

    def test_dict_diff(self):
        """Test dictionary diff generation"""
        original_data = {"key1": "value1", "key2": "value2"}
        edited_data = {"key1": "value1_modified", "key2": "value2", "key3": "value3"}

        diff = self.metaforge_tab._dict_diff(original_data, edited_data)

        # Should return a list of differences
        assert isinstance(diff, list)
        assert len(diff) > 0

    def test_summarize_dict_diff(self):
        """Test diff summarization"""
        original_data = {"key1": "value1", "key2": "value2"}
        edited_data = {"key1": "value1_modified", "key2": "value2", "key3": "value3"}

        summary = self.metaforge_tab._summarize_dict_diff(original_data, edited_data)

        # Should return a string with diff information
        assert isinstance(summary, str)
        assert "🔄" in summary or "➕" in summary  # Using emoji indicators

    @patch("ui.pages.components.film.video_state.load_video")
    def test_handle_publish_without_callback(self, mock_load_video):
        """Test handle publish without custom callback"""
        mock_load_video.return_value = self.mock_video_data

        test_metadata = {"title": "Test", "partners": ["Alice"]}

        # Mock the save_video_metadata function
        with patch("ui.pages.components.film.metaforge_tab.save_video_metadata") as mock_save:
            mock_save.return_value = True

            self.metaforge_tab.handle_publish(test_metadata)

            # Should call save_video_metadata
            mock_save.assert_called_once()

    @patch("ui.pages.components.film.video_state.load_video")
    def test_handle_publish_with_callback(self, mock_load_video):
        """Test handle publish with custom callback"""
        mock_load_video.return_value = self.mock_video_data

        mock_callback = Mock()
        self.metaforge_tab.on_publish = mock_callback

        test_metadata = {"title": "Test", "partners": ["Alice"]}
        self.metaforge_tab.handle_publish(test_metadata)

        # Should call the callback instead of default behavior
        mock_callback.assert_called_once_with(test_metadata)

    @patch("ui.pages.components.film.metaforge_tab.ui")
    def test_add_clip(self, mock_ui):
        """Test adding a clip to the video"""
        # Mock UI timer
        mock_timer = Mock()
        mock_ui.timer = mock_timer

        # Mock the editor container
        self.metaforge_tab.editor_container["ref"] = Mock()
        self.metaforge_tab.editor_container["ref"].run_editor_method = Mock()

        # The _add_clip method doesn't take parameters in the new implementation
        # It generates a new clip internally
        self.metaforge_tab._add_clip()

        # Should call timer to inject the clip
        mock_timer.assert_called_once()

    @patch("ui.pages.components.film.metaforge_tab.ui")
    def test_remove_clip(self, mock_ui):
        """Test removing a clip from the video"""
        mock_notify = Mock()
        mock_ui.notify = mock_notify

        # Mock the video data to have clips
        self.metaforge_tab.video_state._video_data = self.mock_video_data

        self.metaforge_tab._remove_clip("clip1")

        # Should show notification
        mock_notify.assert_called_once()

    @patch("ui.pages.components.film.metaforge_tab.ui")
    def test_update_clip(self, mock_ui):
        """Test updating a clip in the video"""
        mock_notify = Mock()
        mock_ui.notify = mock_notify

        # Mock the video data to have clips
        self.metaforge_tab.video_state._video_data = self.mock_video_data

        updated_clip = {
            "clip_id": "clip1",
            "title": "Updated Clip",
            "start": 0,
            "end": 60,
            "speed": 1.5,
            "description": "Updated description",
            "labels": ["action", "thriller"],
            "partners": ["Alice", "David"],
        }

        self.metaforge_tab._update_clip(updated_clip)

        # Should show notification
        mock_notify.assert_called_once()

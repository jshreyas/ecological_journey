"""
Unit tests for ClipboardTab component
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from ui.film_components.clipboard_tab import ClipboardTab
from ui.film_components.video_state import VideoState


class TestClipboardTab:
    """Test cases for ClipboardTab component"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.video_id = "test_video_123"
        self.mock_video_data = {
            "video_id": "test_video_123",
            "title": "Test Video",
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
                    "labels": ["action"]
                }
            ]
        }
        self.video_state = VideoState(self.video_id)
        self.clipboard_tab = ClipboardTab(self.video_state)
    
    @patch('ui.film_components.video_state.load_video')
    def test_init(self, mock_load_video):
        """Test ClipboardTab initialization"""
        mock_load_video.return_value = self.mock_video_data
        
        assert self.clipboard_tab.video_state == self.video_state
        assert self.clipboard_tab.container is None
        assert self.clipboard_tab.on_edit_clip is None
        assert self.clipboard_tab.on_play_clip is None
        assert self.clipboard_tab.on_share_clip is None
    
    @patch('ui.film_components.video_state.load_video')
    @patch('ui.film_components.clipboard_tab.ui')
    def test_create_tab(self, mock_ui, mock_load_video):
        """Test creating the clipboard tab"""
        mock_load_video.return_value = self.mock_video_data
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)
        
        self.clipboard_tab.create_tab(mock_container)
        
        assert self.clipboard_tab.container == mock_container
    
    @patch('ui.film_components.video_state.load_video')
    @patch('ui.film_components.clipboard_tab.ui')
    def test_refresh_with_container(self, mock_ui, mock_load_video):
        """Test refreshing the clipboard tab with container"""
        mock_load_video.return_value = self.mock_video_data
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)
        
        self.clipboard_tab.container = mock_container
        self.clipboard_tab.refresh()
        
        # Should clear and recreate the UI
        mock_container.clear.assert_called_once()
    
    @patch('ui.film_components.video_state.load_video')
    @patch('ui.film_components.clipboard_tab.ui')
    def test_refresh_without_container(self, mock_ui, mock_load_video):
        """Test refreshing the clipboard tab without container"""
        mock_load_video.return_value = self.mock_video_data
        
        # Should not raise any exceptions
        self.clipboard_tab.refresh()
    
    @patch('ui.film_components.video_state.load_video')
    def test_get_video_data(self, mock_load_video):
        """Test getting video data"""
        mock_load_video.return_value = self.mock_video_data
        
        video_data = self.clipboard_tab.get_video_data()
        
        assert video_data == self.mock_video_data
    
    @patch('ui.film_components.video_state.load_video')
    def test_get_clips(self, mock_load_video):
        """Test getting clips from video data"""
        mock_load_video.return_value = self.mock_video_data
        
        clips = self.clipboard_tab.get_clips()
        
        assert clips == self.mock_video_data["clips"]
    
    @patch('ui.film_components.video_state.load_video')
    def test_get_clips_no_video(self, mock_load_video):
        """Test getting clips when no video data is available"""
        mock_load_video.return_value = None
        
        clips = self.clipboard_tab.get_clips()
        
        assert clips == []
    
    def test_handle_edit_clip(self):
        """Test handling edit clip action"""
        mock_clip = {"clip_id": "test_clip"}
        mock_callback = Mock()
        self.clipboard_tab.on_edit_clip = mock_callback
        
        self.clipboard_tab._handle_edit_clip(mock_clip)
        
        mock_callback.assert_called_once_with(mock_clip)
    
    def test_handle_play_clip(self):
        """Test handling play clip action"""
        mock_clip = {"clip_id": "test_clip"}
        mock_callback = Mock()
        self.clipboard_tab.on_play_clip = mock_callback
        
        self.clipboard_tab._handle_play_clip(mock_clip)
        
        mock_callback.assert_called_once_with(mock_clip)
    
    def test_handle_share_clip(self):
        """Test handling share clip action"""
        mock_clip = {"clip_id": "test_clip"}
        mock_callback = Mock()
        self.clipboard_tab.on_share_clip = mock_callback
        
        self.clipboard_tab._handle_share_clip(mock_clip)
        
        mock_callback.assert_called_once_with(mock_clip)
    
    def test_format_time(self):
        """Test time formatting"""
        # Test seconds
        assert self.clipboard_tab._format_time(30) == "00:30"
        
        # Test minutes and seconds
        assert self.clipboard_tab._format_time(90) == "01:30"
        
        # Test hours, minutes and seconds
        assert self.clipboard_tab._format_time(3661) == "01:01:01"
        
        # Test zero
        assert self.clipboard_tab._format_time(0) == "00:00" 
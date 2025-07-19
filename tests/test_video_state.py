"""
Unit tests for VideoState class
"""
import pytest
from unittest.mock import Mock, patch
from video_state import VideoState


class TestVideoState:
    """Test cases for VideoState class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.video_id = "test_video_123"
        self.mock_video_data = {
            "video_id": "test_video_123",
            "title": "Test Video",
            "clips": [
                {"clip_id": "clip1", "title": "Clip 1"},
                {"clip_id": "clip2", "title": "Clip 2"}
            ],
            "partners": ["Alice", "Bob"],
            "labels": ["action", "drama"],
            "notes": "Test notes"
        }
    
    def test_init(self):
        """Test VideoState initialization"""
        state = VideoState(self.video_id)
        assert state.video_id == self.video_id
        assert state._video_data is None
        assert state._refresh_callbacks == []
    
    @patch('video_state.load_video')
    def test_get_video_loads_data_on_first_call(self, mock_load_video):
        """Test that get_video loads data on first call"""
        mock_load_video.return_value = self.mock_video_data
        state = VideoState(self.video_id)
        
        result = state.get_video()
        
        mock_load_video.assert_called_once_with(self.video_id)
        assert result == self.mock_video_data
        assert state._video_data == self.mock_video_data
    
    @patch('video_state.load_video')
    def test_get_video_uses_cached_data_on_subsequent_calls(self, mock_load_video):
        """Test that get_video uses cached data on subsequent calls"""
        mock_load_video.return_value = self.mock_video_data
        state = VideoState(self.video_id)
        
        # First call - should load data
        result1 = state.get_video()
        # Second call - should use cached data
        result2 = state.get_video()
        
        # load_video should only be called once
        mock_load_video.assert_called_once_with(self.video_id)
        assert result1 == result2 == self.mock_video_data
    
    @patch('video_state.load_video')
    def test_refresh_reloads_data_and_calls_callbacks(self, mock_load_video):
        """Test that refresh reloads data and calls all callbacks"""
        mock_load_video.return_value = self.mock_video_data
        state = VideoState(self.video_id)
        
        # Add some callbacks
        callback1 = Mock()
        callback2 = Mock()
        state.add_refresh_callback(callback1)
        state.add_refresh_callback(callback2)
        
        # Initial load
        state.get_video()
        mock_load_video.reset_mock()
        
        # Refresh
        state.refresh()
        
        # Should reload data
        mock_load_video.assert_called_once_with(self.video_id)
        # Should call all callbacks
        callback1.assert_called_once()
        callback2.assert_called_once()
    
    def test_add_refresh_callback(self):
        """Test adding refresh callbacks"""
        state = VideoState(self.video_id)
        callback = Mock()
        
        state.add_refresh_callback(callback)
        
        assert callback in state._refresh_callbacks
        assert len(state._refresh_callbacks) == 1
    
    def test_remove_refresh_callback(self):
        """Test removing refresh callbacks"""
        state = VideoState(self.video_id)
        callback = Mock()
        
        # Add and then remove callback
        state.add_refresh_callback(callback)
        state.remove_refresh_callback(callback)
        
        assert callback not in state._refresh_callbacks
        assert len(state._refresh_callbacks) == 0
    
    def test_remove_refresh_callback_not_present(self):
        """Test removing a callback that wasn't added"""
        state = VideoState(self.video_id)
        callback = Mock()
        
        # Try to remove callback that wasn't added
        state.remove_refresh_callback(callback)
        
        assert len(state._refresh_callbacks) == 0
    
    def test_clear_cache(self):
        """Test clearing the cache"""
        state = VideoState(self.video_id)
        state._video_data = self.mock_video_data
        
        state.clear_cache()
        
        assert state._video_data is None
    
    @patch('video_state.load_video')
    def test_get_clips(self, mock_load_video):
        """Test getting clips from video data"""
        mock_load_video.return_value = self.mock_video_data
        state = VideoState(self.video_id)
        
        clips = state.get_clips()
        
        assert clips == self.mock_video_data["clips"]
    
    @patch('video_state.load_video')
    def test_get_partners(self, mock_load_video):
        """Test getting partners from video data"""
        mock_load_video.return_value = self.mock_video_data
        state = VideoState(self.video_id)
        
        partners = state.get_partners()
        
        assert partners == self.mock_video_data["partners"]
    
    @patch('video_state.load_video')
    def test_get_labels(self, mock_load_video):
        """Test getting labels from video data"""
        mock_load_video.return_value = self.mock_video_data
        state = VideoState(self.video_id)
        
        labels = state.get_labels()
        
        assert labels == self.mock_video_data["labels"]
    
    @patch('video_state.load_video')
    def test_get_notes(self, mock_load_video):
        """Test getting notes from video data"""
        mock_load_video.return_value = self.mock_video_data
        state = VideoState(self.video_id)
        
        notes = state.get_notes()
        
        assert notes == self.mock_video_data["notes"]
    
    @patch('video_state.load_video')
    def test_get_methods_return_empty_defaults_when_missing(self, mock_load_video):
        """Test that get methods return empty defaults when data is missing"""
        mock_load_video.return_value = {"video_id": "test"}  # Minimal data
        state = VideoState(self.video_id)
        
        assert state.get_clips() == []
        assert state.get_partners() == []
        assert state.get_labels() == []
        assert state.get_notes() == ""
    
    @patch('video_state.load_video')
    def test_refresh_with_no_callbacks(self, mock_load_video):
        """Test refresh works correctly when no callbacks are registered"""
        mock_load_video.return_value = self.mock_video_data
        state = VideoState(self.video_id)
        
        # Should not raise any exceptions
        state.refresh()
        
        mock_load_video.assert_called_once_with(self.video_id) 
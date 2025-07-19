"""
Unit tests for MetaforgeTab component
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from ui.film_components.metaforge_tab import MetaforgeTab
from ui.film_components.video_state import VideoState


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
            "clips": []
        }
        self.video_state = VideoState(self.video_id)
        self.metaforge_tab = MetaforgeTab(self.video_state)
    
    @patch('ui.film_components.video_state.load_video')
    def test_init(self, mock_load_video):
        """Test MetaforgeTab initialization"""
        mock_load_video.return_value = self.mock_video_data
        
        assert self.metaforge_tab.video_state == self.video_state
        assert self.metaforge_tab.container is None
        assert self.metaforge_tab.json_editor is None
        assert self.metaforge_tab.on_publish is None
    
    @patch('ui.film_components.video_state.load_video')
    @patch('ui.film_components.metaforge_tab.ui')
    def test_create_tab(self, mock_ui, mock_load_video):
        """Test creating the metaforge tab"""
        mock_load_video.return_value = self.mock_video_data
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)
        
        self.metaforge_tab.create_tab(mock_container)
        
        assert self.metaforge_tab.container == mock_container
    
    @patch('ui.film_components.video_state.load_video')
    @patch('ui.film_components.metaforge_tab.ui')
    def test_refresh_with_container(self, mock_ui, mock_load_video):
        """Test refreshing the metaforge tab with container"""
        mock_load_video.return_value = self.mock_video_data
        mock_container = Mock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=None)
        
        self.metaforge_tab.container = mock_container
        self.metaforge_tab.refresh()
        
        # Should clear and recreate the UI
        mock_container.clear.assert_called_once()
    
    @patch('ui.film_components.video_state.load_video')
    @patch('ui.film_components.metaforge_tab.ui')
    def test_refresh_without_container(self, mock_ui, mock_load_video):
        """Test refreshing the metaforge tab without container"""
        mock_load_video.return_value = self.mock_video_data
        
        # Should not raise any exceptions
        self.metaforge_tab.refresh()
    
    @patch('ui.film_components.video_state.load_video')
    def test_get_video_data(self, mock_load_video):
        """Test getting video data"""
        mock_load_video.return_value = self.mock_video_data
        
        video_data = self.metaforge_tab.get_video_data()
        
        assert video_data == self.mock_video_data
    
    @patch('ui.film_components.video_state.load_video')
    @patch('ui.film_components.metaforge_tab.ui')
    def test_validate_json_valid(self, mock_ui, mock_load_video):
        """Test JSON validation with valid JSON"""
        mock_load_video.return_value = self.mock_video_data
        
        # Mock the json_editor
        self.metaforge_tab.json_editor = Mock()
        self.metaforge_tab.json_editor.value = '{"test": "value"}'
        
        self.metaforge_tab._validate_json()
        
        # Should not raise any exceptions
        assert True
    
    @patch('ui.film_components.video_state.load_video')
    @patch('ui.film_components.metaforge_tab.ui')
    def test_validate_json_invalid(self, mock_ui, mock_load_video):
        """Test JSON validation with invalid JSON"""
        mock_load_video.return_value = self.mock_video_data
        
        # Mock the json_editor
        self.metaforge_tab.json_editor = Mock()
        self.metaforge_tab.json_editor.value = '{"test": "value"'  # Invalid JSON
        
        self.metaforge_tab._validate_json()
        
        # Should not raise any exceptions
        assert True
    
    def test_generate_diff(self):
        """Test diff generation"""
        original_data = {"key1": "value1", "key2": "value2"}
        edited_data = {"key1": "value1_modified", "key2": "value2", "key3": "value3"}
        
        diff = self.metaforge_tab._generate_diff(original_data, edited_data)
        
        # Should return a string with diff information
        assert isinstance(diff, str)
        assert "Modified" in diff
        assert "Added" in diff
    
    @patch('ui.film_components.video_state.load_video')
    @patch('ui.film_components.metaforge_tab.ui')
    @patch('ui.film_components.metaforge_tab.app')
    def test_handle_publish_without_callback(self, mock_app, mock_ui, mock_load_video):
        """Test handle publish without custom callback"""
        mock_load_video.return_value = self.mock_video_data
        mock_app.storage.user.get.return_value = "test_token"
        
        # Mock the json_editor
        self.metaforge_tab.json_editor = Mock()
        self.metaforge_tab.json_editor.value = '{"title": "Test"}'
        
        # Mock the save_video_metadata function
        with patch('ui.film_components.metaforge_tab.save_video_metadata') as mock_save:
            mock_save.return_value = True
            
            self.metaforge_tab._handle_publish()
            
            # Should call save_video_metadata
            mock_save.assert_called_once()
    
    @patch('ui.film_components.video_state.load_video')
    @patch('ui.film_components.metaforge_tab.ui')
    def test_handle_publish_with_callback(self, mock_ui, mock_load_video):
        """Test handle publish with custom callback"""
        mock_load_video.return_value = self.mock_video_data
        
        mock_callback = Mock()
        self.metaforge_tab.on_publish = mock_callback
        
        test_metadata = {"title": "Test", "partners": ["Alice"]}
        self.metaforge_tab.handle_publish(test_metadata)
        
        # Should call the callback instead of default behavior
        mock_callback.assert_called_once_with(test_metadata)
    
    @patch('ui.film_components.video_state.load_video')
    def test_add_clip(self, mock_load_video):
        """Test adding a clip to the video"""
        mock_load_video.return_value = self.mock_video_data
        
        new_clip = {
            "clip_id": "new_clip",
            "title": "New Clip",
            "start": 0,
            "end": 30,
            "speed": 1.0,
            "description": "New clip description",
            "labels": ["comedy"],
            "partners": ["Charlie"]
        }
        
        # Mock UI components
        with patch('ui.film_components.metaforge_tab.ui') as mock_ui:
            mock_notify = Mock()
            mock_ui.notify = mock_notify
            
            self.metaforge_tab._add_clip(new_clip)
            
            # Should show notification
            mock_notify.assert_called_once()
    
    @patch('ui.film_components.video_state.load_video')
    def test_remove_clip(self, mock_load_video):
        """Test removing a clip from the video"""
        mock_load_video.return_value = self.mock_video_data
        
        clip_id = "clip1"
        
        # Mock UI components
        with patch('ui.film_components.metaforge_tab.ui') as mock_ui:
            mock_notify = Mock()
            mock_ui.notify = mock_notify
            
            self.metaforge_tab._remove_clip(clip_id)
            
            # Should show notification
            mock_notify.assert_called_once()
    
    @patch('ui.film_components.video_state.load_video')
    def test_update_clip(self, mock_load_video):
        """Test updating a clip in the video"""
        mock_load_video.return_value = self.mock_video_data
        
        updated_clip = {
            "clip_id": "clip1",
            "title": "Updated Clip",
            "start": 0,
            "end": 60,
            "speed": 1.5,
            "description": "Updated description",
            "labels": ["action", "thriller"],
            "partners": ["Alice", "David"]
        }
        
        # Mock UI components
        with patch('ui.film_components.metaforge_tab.ui') as mock_ui:
            mock_notify = Mock()
            mock_ui.notify = mock_notify
            
            self.metaforge_tab._update_clip(updated_clip)
            
            # Should show notification
            mock_notify.assert_called_once() 
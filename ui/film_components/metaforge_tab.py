"""
MetaforgeTab - Component for bulk editing video metadata
Handles the metaforge functionality for bulk editing
"""
from nicegui import ui, app
from utils.utils_api import save_video_metadata
from .video_state import VideoState
from typing import Callable, Optional
import json


class MetaforgeTab:
    """Component for bulk editing video metadata"""
    
    def __init__(self, video_state: VideoState, on_publish: Callable = None):
        self.video_state = video_state
        self.on_publish = on_publish
        self.container = None
        self.json_editor = None
        self.diff_area = None
        self.confirm_dialog = None
        
        # Register for video state refresh notifications
        self.video_state.add_refresh_callback(self.refresh)
    
    def create_tab(self, container):
        """Create the metaforge tab UI"""
        self.container = container
        self.refresh()
    
    def refresh(self):
        """Refresh the metaforge tab with current video data"""
        if not self.container:
            return
            
        self.container.clear()
        with self.container:
            self._create_metaforge_ui()
    
    def _create_metaforge_ui(self):
        """Create the metaforge editing UI"""
        video = self.video_state.get_video()
        if not video:
            ui.label("No video data available")
            return
        
        # Create JSON editor
        video_json = json.dumps(video, indent=2)
        self.json_editor = ui.textarea(
            'Edit JSON',
            value=video_json,
            on_change=self._on_json_change
        ).props('rows=20').classes('w-full font-mono text-sm')
        
        # Action buttons
        with ui.row().classes('justify-between gap-2 mt-4'):
            with ui.row().classes('gap-2'):
                ui.button(icon='refresh', on_click=self._reset_json).props('color=secondary')
                ui.button(icon='validate', on_click=self._validate_json).props('color=info')
                ui.button(icon='diff', on_click=self._show_diff).props('color=warning')
            
            ui.button(icon='publish', on_click=self._handle_publish).props('color=primary')
    
    def _on_json_change(self):
        """Handle JSON editor changes"""
        # This could trigger validation or diff generation
        pass
    
    def _reset_json(self):
        """Reset JSON to original video data"""
        video = self.video_state.get_video()
        if video and self.json_editor:
            self.json_editor.value = json.dumps(video, indent=2)
            ui.notify("✅ JSON reset to original data", type="positive")
    
    def _validate_json(self):
        """Validate the JSON in the editor"""
        if not self.json_editor:
            return
        
        try:
            json_data = json.loads(self.json_editor.value)
            ui.notify("✅ JSON is valid", type="positive")
        except json.JSONDecodeError as e:
            ui.notify(f"❌ Invalid JSON: {e}", type="negative")
    
    def _show_diff(self):
        """Show diff between original and edited data"""
        if not self.json_editor:
            return
        
        try:
            original_data = self.video_state.get_video()
            edited_data = json.loads(self.json_editor.value)
            
            diff = self._generate_diff(original_data, edited_data)
            
            # Show diff in a dialog
            with ui.dialog() as dialog, ui.card():
                ui.label('Changes Preview').classes('text-lg font-bold mb-2')
                ui.markdown(diff).classes('text-sm max-h-80 overflow-auto')
                with ui.row().classes('justify-end gap-2 mt-4'):
                    ui.button('Close', on_click=dialog.close).props('flat')
                    ui.button('Publish', on_click=lambda: [dialog.close(), self._handle_publish()]).props('color=primary')
            dialog.open()
            
        except json.JSONDecodeError:
            ui.notify("❌ Invalid JSON - cannot generate diff", type="negative")
    
    def _generate_diff(self, original_data, edited_data):
        """Generate a diff between original and edited data"""
        # Simple diff implementation
        diff_lines = []
        
        # Compare top-level keys
        all_keys = set(original_data.keys()) | set(edited_data.keys())
        
        for key in sorted(all_keys):
            if key not in original_data:
                diff_lines.append(f"➕ **{key}**: Added")
            elif key not in edited_data:
                diff_lines.append(f"➖ **{key}**: Removed")
            elif original_data[key] != edited_data[key]:
                diff_lines.append(f"🔄 **{key}**: Modified")
                if isinstance(original_data[key], dict) and isinstance(edited_data[key], dict):
                    # Recursive diff for nested objects
                    nested_diff = self._generate_diff(original_data[key], edited_data[key])
                    diff_lines.extend([f"  {line}" for line in nested_diff.split('\n') if line.strip()])
        
        return '\n'.join(diff_lines) if diff_lines else "No changes detected"
    
    def _handle_publish(self):
        """Handle publish operation"""
        if not self.json_editor:
            return
        
        try:
            edited_data = json.loads(self.json_editor.value)
            
            if self.on_publish:
                self.on_publish(edited_data)
            else:
                # Default publish behavior
                token = app.storage.user.get("token")
                if not token:
                    ui.notify("❌ Authentication required", type="negative")
                    return
                
                success = save_video_metadata(edited_data, token)
                if success:
                    ui.notify("✅ Metadata published successfully", type="positive")
                    self.video_state.refresh()
                else:
                    ui.notify("❌ Failed to publish metadata", type="negative")
                    
        except json.JSONDecodeError:
            ui.notify("❌ Invalid JSON - cannot publish", type="negative")
        except Exception as e:
            ui.notify(f"❌ Error publishing: {e}", type="negative")
    
    def handle_publish(self, video_metadata=None):
        """Handle publish operation with custom callback"""
        if self.on_publish:
            self.on_publish(video_metadata)
        else:
            # Default publish behavior
            token = app.storage.user.get("token")
            if not token:
                ui.notify("❌ Authentication required", type="negative")
                return
            
            try:
                video = self.video_state.get_video()
                if not video:
                    ui.notify("❌ No video data available", type="negative")
                    return
                
                # Merge with required fields from the loaded video
                for key in ["video_id", "youtube_url", "title", "date", "duration_seconds"]:
                    video_metadata[key] = video.get(key)
                # Preserve existing clips!
                video_metadata["clips"] = video.get("clips", [])
                
                success = save_video_metadata(video_metadata, token)
                if success:
                    ui.notify("✅ Metadata published", type="positive")
                else:
                    ui.notify("❌ Failed to publish metadata", type="negative")
            except Exception as e:
                ui.notify(f"❌ Error: {e}", type="negative")
    
    def get_video_data(self):
        """Get the current video data"""
        return self.video_state.get_video()
    
    def _add_clip(self, clip_data):
        """Add a clip to the video"""
        video_data = self.get_video_data()
        if video_data:
            if 'clips' not in video_data:
                video_data['clips'] = []
            video_data['clips'].append(clip_data)
            ui.notify("✅ Clip added successfully", type="positive")
    
    def _remove_clip(self, clip_id):
        """Remove a clip from the video"""
        video_data = self.get_video_data()
        if video_data and 'clips' in video_data:
            video_data['clips'] = [c for c in video_data['clips'] if c.get('clip_id') != clip_id]
            ui.notify("✅ Clip removed successfully", type="positive")
    
    def _update_clip(self, clip_data):
        """Update a clip in the video"""
        video_data = self.get_video_data()
        if video_data and 'clips' in video_data:
            for i, clip in enumerate(video_data['clips']):
                if clip.get('clip_id') == clip_data.get('clip_id'):
                    video_data['clips'][i] = clip_data
                    break
            ui.notify("✅ Clip updated successfully", type="positive") 
"""
PlayerControlsTab - Component for video player controls and playlist functionality
Handles the video player controls and playlist mode
"""

from typing import Callable

from nicegui import ui
from utils.hls_player import HLSPlayer
from utils.utils_api import load_video
from utils.video_player import VideoPlayer

from .video_state import VideoState


class PlayerControlsTab:
    """Component for video player controls and playlist functionality"""

    def __init__(self, video_state: VideoState, on_clip_play: Callable = None):
        self.video_state = video_state
        self.on_clip_play = on_clip_play
        self.container = None
        self.player_container = {"ref": None}
        self.player_speed = {"value": 1.0}
        self.clips_playlist_state = {"index": 0, "clips": []}

    def create_tab(self, container, play_clips_playlist=False, autoplay_clip=None):
        """Create the player controls tab UI"""
        self.container = container
        self.refresh(play_clips_playlist, autoplay_clip)

    def refresh(self, play_clips_playlist=False, autoplay_clip=None):
        """Refresh the player controls with current video data"""
        if not self.container:
            return

        self.container.clear()
        with self.container:
            player_container_classes = "w-full h-full p-4 gap-4"
            with ui.column().classes(player_container_classes) as player_container_ref:
                self.player_container["ref"] = player_container_ref
                if play_clips_playlist:
                    with player_container_ref:
                        self.play_clips_playlist_mode()
                elif autoplay_clip:
                    self.play_clip(autoplay_clip)
                else:
                    if self.video_state.is_peertube():
                        HLSPlayer(
                            hls_url=self.video_state.get_url(),
                            parent=player_container_ref,
                            on_end=lambda: self.refresh(),
                        )
                    else:
                        VideoPlayer(
                            self.video_state.video_id,
                            speed=self.player_speed["value"],
                            parent=player_container_ref,
                        )

    def play_clip(self, clip):
        """Play a specific clip (without navigation)"""
        ui.notify(
            f"▶️ Playing: {clip['title']} at {clip.get('speed', 1.0)}x",
            type="info",
            position="bottom",
            timeout=3000,
        )
        start_time = clip.get("start", 0)
        end_time = clip.get("end")
        speed = clip.get("speed", 1.0)
        ref = self.player_container["ref"]

        if ref:
            ref.clear()
            with ref:
                if self.video_state.is_peertube():
                    HLSPlayer(
                        hls_url=self.video_state.get_url(),
                        start=start_time,
                        end=end_time,
                        speed=speed,
                        on_end=lambda: self._advance_clip(),
                        parent=ref,
                    )
                else:
                    VideoPlayer(
                        self.video_state.video_id,
                        start=start_time,
                        end=end_time,
                        speed=speed,
                        on_end=lambda: self._advance_clip(),
                        parent=ref,
                    )

    def play_clips_playlist_mode(self):
        """Play all clips in sequence"""
        video = load_video(self.video_state.video_id)
        clips = video.get("clips", [])
        if not clips:
            ui.notify("No clips to play.", type="warning")
            return

        self.clips_playlist_state["clips"] = clips
        self.clips_playlist_state["index"] = 0
        self._play_next_clip()

    def _play_next_clip(self):
        """Play the next clip in the playlist"""
        idx = self.clips_playlist_state["index"]
        clips = self.clips_playlist_state["clips"]
        ref = self.player_container["ref"]
        if idx >= len(clips):
            if ref:
                with ref:
                    ref.clear()  # Remove the player so it can't auto-replay
                    ui.notify("Playlist finished.", type="info")
                    # Optionally, show replay button
                    with ui.row().classes("justify-center gap-4 mt-2"):
                        ui.button("Replay Playlist", on_click=self.play_clips_playlist_mode).props("color=primary")
            return

        clip = clips[idx]
        self.play_clip(clip)

    def _advance_clip(self):
        """Advance to the next clip in the playlist"""
        ref = self.player_container["ref"]
        if ref:
            with ref:
                self.clips_playlist_state["index"] += 1
                self._play_next_clip()

    def set_player_speed(self, speed: float):
        """Set the player speed"""
        self.player_speed["value"] = speed

    def get_player_speed(self) -> float:
        """Get the current player speed"""
        return self.player_speed["value"]

    def get_player_container(self):
        """Get the player container reference"""
        return self.player_container["ref"]

    def _on_clip_end(self, clip, on_next_clip=None):
        ref = self.player_container["ref"]
        if ref:
            with ref:
                ui.notify("Clip ended.", type="info")
                with ui.row().classes("justify-center gap-4 mt-2"):
                    ui.button("Replay Clip", on_click=lambda: self.play_clip(clip)).props("color=primary")
                    if on_next_clip:
                        ui.button("Play Next", on_click=on_next_clip).props("color=secondary")

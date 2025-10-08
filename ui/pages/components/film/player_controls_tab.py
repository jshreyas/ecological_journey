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
                        )
                    else:
                        VideoPlayer(
                            self.video_state.video_id,
                            speed=self.player_speed["value"],
                            parent=player_container_ref,
                        )

    def play_clip(self, clip):
        """Play a specific clip"""
        if self.on_clip_play:
            self.on_clip_play(clip)
        else:
            ui.notify(
                f"▶️ Playing: {clip['title']} at {clip.get('speed', 1.0)}x",
                type="info",
                position="bottom",
                timeout=3000,
            )
            start_time = clip.get("start", 0)
            speed = clip.get("speed", 1.0)
            ref = self.player_container["ref"]
            if ref:
                ref.clear()
                with ref:
                    if self.video_state.is_peertube():
                        # Avoid reloading the same page if already showing this clip
                        request = ui.context.client.request
                        if request.query_params.get("clip") != clip.get("clip_id"):
                            ui.navigate.to(f"/film/{self.video_state.video_id}?clip={clip.get('clip_id')}")
                        else:
                            # TODO: BUG: this scenario does not work, displays a greyed out smaller size HLS player
                            with ui.column().classes("w-full h-full") as player_ref:
                                HLSPlayer(
                                    hls_url=self.video_state.get_url(),
                                    start=start_time,
                                    end=clip.get("end"),
                                    speed=speed,
                                    parent=player_ref,
                                )
                    else:
                        VideoPlayer(
                            self.video_state.video_id,
                            start=start_time,
                            end=clip.get("end"),
                            speed=speed,
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
        if idx >= len(self.clips_playlist_state["clips"]):
            return

        clip = self.clips_playlist_state["clips"][idx]
        start_time = clip.get("start", 0)
        end_time = clip.get("end")
        speed = clip.get("speed", 1.0)
        ref = self.player_container["ref"]

        if ref:
            ref.clear()
            with ref:
                VideoPlayer(
                    self.video_state.video_id,
                    start=start_time,
                    end=end_time,
                    speed=speed,
                    on_end=lambda: self._next_clip_callback(),
                    parent=ref,
                )

    def _next_clip_callback(self):
        """Callback for when a clip ends in playlist mode"""
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

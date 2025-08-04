"""
Film UI Components Package

This package contains all the UI components used by the film page.
"""

from .clipboard_tab import ClipboardTab
from .filmboard_tab import FilmboardTab
from .metaforge_tab import MetaforgeTab
from .navigation_tab import NavigationTab
from .player_controls_tab import PlayerControlsTab
from .share_dialog_tab import ShareDialogTab
from .video_state import VideoState

__all__ = [
    "VideoState",
    "ClipboardTab",
    "MetaforgeTab",
    "FilmboardTab",
    "NavigationTab",
    "PlayerControlsTab",
    "ShareDialogTab",
]

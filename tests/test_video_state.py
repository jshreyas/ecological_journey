from copy import deepcopy
from unittest.mock import Mock

import pytest

from ui.pages.components.film import video_state as video_state_module
from ui.pages.components.film.video_state import VideoState


@pytest.fixture
def video_data():
    return {
        "video_id": "video-1",
        "title": "Training",
        "duration_seconds": 3600,
        "notes": "Original notes",
        "partners": [],
        "labels": [],
        "anchors": [{"anchor_id": "anchor-1", "start": 10, "title": "Entry", "description": ""}],
        "clips": [
            {
                "clip_id": "clip-1",
                "start": 20,
                "end": 40,
                "title": "Sweep",
                "description": "",
                "speed": 1.0,
                "labels": [],
                "partners": [],
            }
        ],
    }


@pytest.fixture
def video_state(monkeypatch, video_data):
    load_video = Mock(return_value=deepcopy(video_data))
    load_videos = Mock(return_value=[])
    monkeypatch.setattr(video_state_module, "load_video", load_video)
    monkeypatch.setattr(video_state_module, "lvs", load_videos)
    return VideoState("video-1"), load_video, load_videos


def test_initialization_loads_metadata_once(video_state):
    state, load_video, _ = video_state

    assert state.video_id == "video-1"
    assert state.get_video()["title"] == "Training"
    assert state.video_description_draft == "Original notes"
    assert state.anchor_draft[0]["anchor_id"] == "anchor-1"
    assert state.clip_draft[0]["clip_id"] == "clip-1"
    load_video.assert_called_once_with("video-1")


def test_get_video_returns_cached_data(video_state):
    state, load_video, _ = video_state

    assert state.get_video() is state.get_video()
    load_video.assert_called_once_with("video-1")


def test_refresh_reloads_video_and_notifies_registered_callbacks(video_state):
    state, load_video, load_videos = video_state
    callback = Mock()
    state.add_refresh_callback(callback)

    state.refresh()

    load_videos.assert_called_once_with()
    assert load_video.call_count == 2
    callback.assert_called_once_with()


def test_playback_updates_active_anchor_and_clip(video_state):
    state, _, _ = video_state
    playback_callback = Mock()
    timeline_callback = Mock()
    state.add_playback_callback(playback_callback)
    state.add_timeline_callback(timeline_callback)

    state.set_playback_time(25)

    assert state.current_playback_time == 25
    assert state.active_anchor_id == "anchor-1"
    assert state.active_metadata_row_id == "clip-1"
    timeline_callback.assert_called_once_with()
    playback_callback.assert_called_once_with()

    state.set_playback_time(15)

    assert state.active_metadata_row_id == "anchor-1"
    assert playback_callback.call_count == 2


def test_save_video_metadata_extracts_tags_and_clears_dirty_flags(video_state, monkeypatch):
    state, _, _ = video_state
    save_metadata = Mock()
    monkeypatch.setattr(video_state_module, "svm", save_metadata)
    state.video_description_draft = "Notes #guard @Alice"
    state.clip_draft[0]["description"] = "Sweep #transition @Bob"
    state.mark_metadata_dirty()

    state.save_video_metadata()

    saved_video = save_metadata.call_args.kwargs["video_metadata"]
    assert saved_video["notes"] == "Notes #guard @Alice"
    assert set(saved_video["labels"]) == {"guard"}
    assert set(saved_video["partners"]) == {"Alice"}
    assert set(saved_video["clips"][0]["labels"]) == {"transition"}
    assert set(saved_video["clips"][0]["partners"]) == {"Bob"}
    assert state._metadata_dirty is False
    assert state.video_description_dirty is False
    save_metadata.assert_called_once()


@pytest.mark.parametrize(
    ("timestamp", "expected"),
    [
        ("1:02", 62),
        ("1:02:03", 3723),
    ],
)
def test_parse_timestamp_accepts_supported_formats(video_state, timestamp, expected):
    state, _, _ = video_state

    assert state._parse_timestamp(timestamp, "test time") == expected


def test_parse_timestamp_rejects_malformed_values(video_state):
    state, _, _ = video_state

    with pytest.raises(ValueError, match="Expected mm:ss or hh:mm:ss"):
        state._parse_timestamp("1:2", "clip start")


def test_convert_anchor_to_clip_moves_draft_and_notifies_refresh(video_state):
    state, _, _ = video_state
    state.anchor_draft[0]["id"] = "anchor-row-1"
    callback = Mock()
    state.add_refresh_callback(callback)

    state.convert_anchor_to_clip("anchor-row-1", end_time=30)

    assert state.anchor_draft == []
    assert state.clip_draft[-1]["start"] == 10
    assert state.clip_draft[-1]["end"] == 30
    assert state._metadata_dirty is True
    callback.assert_called_once_with()

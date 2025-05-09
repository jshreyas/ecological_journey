import pytest
from unittest.mock import patch, mock_open
from utils import (
    parse_clip_line,
    parse_raw_text,
    convert_clips_to_raw_text,
    format_time,
    load_clips,
    load_videos
)

# 1. Tests for parse_clip_line
@pytest.mark.parametrize("line,expected", [
    ("00:00 - 00:30 | Armbar Setup | Controlled entry @john #submission", {
        "start": 0,
        "end": 30,
        "title": "Armbar Setup",
        "description": "Controlled entry",
        "type": "clip",
        "partners": ["john"],
        "labels": ["submission"]
    }),
    ("Invalid Line", None),
    ("Clip Title Here | Just filler", None),
])
def test_parse_clip_line(line, expected):
    assert parse_clip_line(line) == expected

# 2. Tests for parse_raw_text
@pytest.mark.parametrize("raw_text,expected", [
    ("""@carla #mount
type: drilling
notes: test
00:00 - 00:10 | Drill 1 | Practice movement @carla #drill""",
     ([{
        "start": 0,
        "end": 10,
        "title": "Drill 1",
        "description": "Practice movement",
        "type": "clip",
        "partners": ["carla"],
        "labels": ["drill"]
     }], {
         "partners": ["carla"],
         "positions": ["mount"],
         "type": "drilling",
         "notes": "test"
     })
    ),
    ("""@ana #guard
type: positional
notes: metadata only""",
     ([], {
         "partners": ["ana"],
         "positions": ["guard"],
         "type": "positional",
         "notes": "metadata only"
     })
    )
])
def test_parse_raw_text(raw_text, expected):
    assert parse_raw_text(raw_text) == expected

# 3. Test for convert_clips_to_raw_text
@patch("utils.load_clips")
@patch("utils.load_videos")
def test_convert_clips_to_raw_text(mock_load_videos, mock_load_clips):
    mock_load_videos.return_value = [{
        "video_id": "abc123",
        "partners": ["carla"],
        "positions": ["mount"],
        "type": "rolling",
        "notes": "test note",
        "duration_seconds": 120
    }]
    mock_load_clips.return_value = [{
        "start": 0,
        "end": 30,
        "title": "Clip Title",
        "description": "desc",
        "type": "clip",
        "partners": ["carla"],
        "labels": ["drill"]
    }]

    result = convert_clips_to_raw_text("abc123")
    assert "@carla" in result
    assert "#mount" in result
    assert "type: rolling" in result
    assert "notes: test note" in result
    assert "00:00 - 00:30 | Clip Title" in result

# 4. Test for format_time
@pytest.mark.parametrize("seconds,expected", [
    (75, "01:15"),
    (0, "00:00"),
    (599, "09:59")
])
def test_format_time(seconds, expected):
    from utils import format_time  # in case of circular import
    assert format_time(seconds) == expected

# 5. Stub for load_clips and load_videos (already mocked above in test 3)

from unittest.mock import Mock

import pytest

from ui.utils import utils as utils_module


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "0:00"),
        (75, "1:15"),
        (3600, "1:00:00"),
        (3661, "1:01:01"),
    ],
)
def test_format_time(seconds, expected):
    assert utils_module.format_time(seconds) == expected


def test_query_expression_obeys_not_then_and_then_or_precedence():
    matches = utils_module.parse_query_expression(["guard", "OR", "sweep", "AND", "NOT", "closed"])

    assert matches(["guard"])
    assert matches(["sweep"])
    assert not matches(["sweep", "closed"])
    assert not matches(["closed"])


def test_navigate_to_film_includes_optional_clip_id(monkeypatch):
    navigate = Mock()
    monkeypatch.setattr(utils_module.ui.navigate, "to", navigate)

    utils_module.navigate_to_film("video-1", "clip-2")

    navigate.assert_called_once_with("/film/video-1?clip=clip-2")


def test_human_stamp_formats_utc_timestamp():
    assert utils_module.human_stamp("2024-09-23T00:29:00Z") == "Sep 23, 12:29 AM"


def test_format_date_formats_iso_date():
    assert utils_module.format_date("2026-04-02T10:00:00") == "Thursday, Apr 02, 2026"

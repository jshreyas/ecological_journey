from unittest.mock import Mock

from ui.utils import utils_api as utils_api_module


def test_load_playlists_for_user_separates_owned_and_team_playlists(monkeypatch):
    playlists = [
        {"_id": "owned", "owner_id": "user-1", "team_id": None},
        {"_id": "team", "owner_id": "user-2", "team_id": "team-1"},
        {"_id": "private", "owner_id": "user-2", "team_id": "team-2"},
    ]
    monkeypatch.setattr(utils_api_module, "load_playlists", Mock(return_value=playlists))
    monkeypatch.setattr(
        utils_api_module,
        "fetch_teams_for_user",
        Mock(
            return_value={
                "owned": [],
                "member": [{"_id": "team-1", "member_ids": ["user-1"]}],
            }
        ),
    )

    result = utils_api_module.load_playlists_for_user("user-1")

    assert [playlist["_id"] for playlist in result["owned"]] == ["owned"]
    assert [playlist["_id"] for playlist in result["member"]] == ["team"]


def test_load_playlists_for_user_applies_filter(monkeypatch):
    playlists = [
        {"_id": "owned", "owner_id": "user-1", "team_id": None},
        {"_id": "team", "owner_id": "user-2", "team_id": "team-1"},
    ]
    monkeypatch.setattr(utils_api_module, "load_playlists", Mock(return_value=playlists))
    monkeypatch.setattr(
        utils_api_module,
        "fetch_teams_for_user",
        Mock(
            return_value={
                "owned": [],
                "member": [{"_id": "team-1", "member_ids": ["user-1"]}],
            }
        ),
    )

    result = utils_api_module.load_playlists_for_user("user-1", filter="member")

    assert result == {"owned": [], "member": [playlists[1]]}


def test_load_videos_adds_playlist_and_duration_data_and_sorts(monkeypatch):
    monkeypatch.setattr(
        utils_api_module,
        "load_playlists",
        Mock(return_value=[{"_id": "playlist-1"}]),
    )
    monkeypatch.setattr(
        utils_api_module,
        "load_playlist",
        Mock(
            return_value={
                "_id": "playlist-1",
                "name": "Training",
                "color": "blue",
                "videos": [
                    {"video_id": "older", "date": "2024-01-01", "duration_seconds": 75},
                    {
                        "video_id": "newer",
                        "date": "2024-02-01",
                        "duration_seconds": 3661,
                    },
                ],
            }
        ),
    )

    videos = utils_api_module.load_videos()

    assert [video["video_id"] for video in videos] == ["newer", "older"]
    assert videos[0]["playlist_name"] == "Training"
    assert videos[0]["playlist_color"] == "blue"
    assert videos[0]["duration_human"] == "01:01:01"
    assert videos[1]["duration_human"] == "01:15"


def test_get_filtered_clips_combines_playlist_date_label_and_partner_filters(
    monkeypatch,
):
    clips = [
        {
            "playlist_name": "Training",
            "date": "2024-03-01",
            "labels": ["guard"],
            "partners": ["Alice"],
        },
        {
            "playlist_name": "Training",
            "date": "2024-03-01",
            "labels": ["guard", "closed"],
            "partners": ["Alice"],
        },
        {
            "playlist_name": "Training",
            "date": "2024-04-01",
            "labels": ["guard"],
            "partners": ["Alice"],
        },
        {
            "playlist_name": "Other",
            "date": "2024-03-01",
            "labels": ["guard"],
            "partners": ["Alice"],
        },
    ]
    monkeypatch.setattr(utils_api_module, "load_clips", Mock(return_value=clips))
    monkeypatch.setattr(
        utils_api_module,
        "load_cliplist",
        Mock(
            return_value={
                "filters": {
                    "playlists": ["Training"],
                    "date_range": ["2024-03-01", "2024-03-31"],
                    "labels": ["guard", "AND", "NOT", "closed"],
                    "partners": ["Alice"],
                }
            }
        ),
    )

    assert utils_api_module.get_filtered_clips("list-1") == [clips[0]]

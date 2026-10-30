from unittest.mock import Mock

from bson import ObjectId

from ui.data.crud import delete_videos_from_playlist
from ui.data.models import Playlist, Video


def test_delete_videos_from_playlist_removes_requested_ids(monkeypatch):
    playlist = Playlist(
        name="Test Playlist",
        playlist_id="PLTEST",
        videos=[
            Video(
                video_id="keep_me",
                youtube_url="https://youtu.be/keep_me",
                title="Keep Me",
                date="2024-01-01T00:00:00Z",
                duration_seconds=123,
                partners=[],
                positions=[],
                notes="",
                labels=[],
                clips=[],
                anchors=[],
            ),
            Video(
                video_id="remove_me",
                youtube_url="https://youtu.be/remove_me",
                title="Remove Me",
                date="2024-01-01T00:00:00Z",
                duration_seconds=123,
                partners=[],
                positions=[],
                notes="",
                labels=[],
                clips=[],
                anchors=[],
            ),
        ],
        owner_id=ObjectId(),
        team_id=None,
        color="bg-gray-300",
    )
    playlist.id = ObjectId()
    save = Mock()
    monkeypatch.setattr(Playlist, "save", save)

    class DummyPlaylistQuery:
        def __init__(self, obj):
            self.obj = obj

        def run(self):
            return self.obj

    monkeypatch.setattr(Playlist, "find_one", lambda *args, **kwargs: DummyPlaylistQuery(playlist))

    user = type("UserStub", (), {"role": "service", "id": ObjectId()})()

    result = delete_videos_from_playlist.__wrapped__(
        playlist_id=str(playlist.id),
        video_ids=["remove_me"],
        user=user,
    )

    remaining_ids = [video["video_id"] for video in result["videos"]]

    assert remaining_ids == ["keep_me"]
    assert len(result["videos"]) == 1
    save.assert_called_once()

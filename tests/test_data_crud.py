import pytest
from bson import ObjectId
from bunnet import Document

from ui.data import crud
from ui.data.auth import AuthError
from ui.data.models import Clip, Playlist, User, Video


def make_user(role="user", user_id=None):
    user = User(username="alice", email="alice@example.com", role=role)
    if user_id is not None:
        user.id = user_id
    return user


def test_can_write_playlist_for_owner_and_privileged_roles():
    owner_id = ObjectId()
    playlist = Playlist(name="Training", owner_id=owner_id)

    assert crud.can_write_playlist(make_user(user_id=owner_id), playlist)
    assert crud.can_write_playlist(make_user(role="admin"), playlist)
    assert crud.can_write_playlist(make_user(role="service"), playlist)
    assert not crud.can_write_playlist(make_user(), playlist)


def test_require_admin_or_service_rejects_regular_user():
    with pytest.raises(AuthError, match="Admin or service permission required"):
        crud.require_admin_or_service(make_user())


def test_apply_training_date_logic_preserves_publish_date_without_mutation():
    video = {"date": "2024-01-01", "training_date": "2024-02-01"}

    result = crud.apply_training_date_logic(video)

    assert result == {
        "date": "2024-02-01",
        "training_date": "2024-02-01",
        "publish_date": "2024-01-01",
    }
    assert video == {"date": "2024-01-01", "training_date": "2024-02-01"}


def test_to_dicts_recursively_converts_document_and_object_ids():
    document = Video(
        video_id="video-1",
        youtube_url="https://youtu.be/video-1",
        title="Training",
        date="2024-01-01",
        duration_seconds=60,
    )

    result = crud.to_dicts({"document": document, "ids": (document.id, ObjectId())})

    assert isinstance(result["document"], dict)
    assert result["document"]["_id"] == str(document.id)
    assert all(isinstance(value, str) for value in result["ids"])
    assert issubclass(Video, Document)


def test_merge_embedded_docs_preserves_matching_ids_and_drops_removed_docs():
    existing = [
        Clip(clip_id="keep", start=1, end=3, description="old", title="Sweep"),
        Clip(clip_id="remove", start=5, end=7, description="", title="Pass"),
    ]
    updated = [Clip(clip_id="keep", start=2, end=4, description="updated", title="Sweep")]

    result = crud.merge_embedded_docs(
        existing_docs=existing,
        updated_docs=updated,
        id_field="clip_id",
        doc_cls=Clip,
    )

    assert len(result) == 1
    assert result[0].clip_id == "keep"
    assert result[0].start == 2
    assert result[0].description == "updated"

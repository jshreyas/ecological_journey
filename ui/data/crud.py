import os
import threading
from datetime import datetime
from typing import Any, Dict, Optional, ParamSpec, TypeVar
from uuid import uuid4

from bson import ObjectId
from bunnet import Document
from dotenv import load_dotenv

from ui.data.auth import AuthError, create_access_token, verify_password
from ui.data.models import Anchor, Clip, Cliplist, Feedback, Learnings, Notion, Playlist, Team, User, Video
from ui.log import log
from ui.utils.cache import cache_result, clear_all_caches, invalidate_cache
from ui.utils.notion import generate_tree

P = ParamSpec("P")
R = TypeVar("R")
load_dotenv()

CACHE_TTL = int(os.getenv("CACHE_TTL", 604800))  # Cache TTL in seconds


def require_admin_or_service(user: User) -> None:
    if user.role not in {"admin", "service"}:
        raise AuthError("Admin or service permission required")


def can_write_playlist(user: User, playlist: Playlist) -> bool:
    if user.role in {"admin", "service"}:
        return True

    if playlist.owner_id == user.id:
        return True

    # TODO: Add this when Playlist.team_id and Team membership are enforced:
    # if playlist.team_id and user.id in team.member_ids:
    #     return True

    return False


def get_or_create_user(
    email: str,
    username: str,
    oauth_provider: str,
    oauth_sub: str,
) -> User:
    """Return the existing user, or create and return a User document."""
    existing_user = load_user_by_oauth(oauth_provider, oauth_sub)

    if existing_user:
        # Optional: update display attributes from the current OAuth profile.
        existing_user.username = username
        existing_user.email = email
        existing_user.save()
        return existing_user

    # If OAuth subject was not found, optionally fall back to email.
    existing_user = load_user_by_email(email)
    if existing_user:
        existing_user.username = username
        existing_user.oauth_provider = oauth_provider
        existing_user.oauth_sub = oauth_sub
        existing_user.save()
        return existing_user

    return create_user(
        email=email,
        username=username,
        oauth_provider=oauth_provider,
        oauth_sub=oauth_sub,
    )


def create_user(
    email: str,
    username: str,
    oauth_provider: str,
    oauth_sub: str,
) -> User:
    user = User(
        username=username,
        email=email,
        oauth_provider=oauth_provider,
        oauth_sub=oauth_sub,
        hashed_password=None,
    )
    user.insert()
    return user


def load_user_by_email(email: str) -> User | None:
    return User.find_one(User.email == email).run()


def load_user_by_oauth(
    oauth_provider: str,
    oauth_sub: str,
) -> User | None:
    return User.find_one(
        User.oauth_provider == oauth_provider,
        User.oauth_sub == oauth_sub,
    ).run()


def to_dicts(obj: Any) -> Any:
    # Case 1: Bunnet or Pydantic document
    if isinstance(obj, Document):
        return to_dicts(obj.model_dump(mode="json", by_alias=True))

    # Case 2: ObjectId
    elif isinstance(obj, ObjectId):
        return str(obj)

    # Case 3: Dict (recursively process keys and values)
    elif isinstance(obj, dict):
        return {k: to_dicts(v) for k, v in obj.items()}

    # Case 4: List or tuple
    elif isinstance(obj, (list, tuple)):
        return [to_dicts(item) for item in obj]

    # Case 5: Anything else (primitive types, etc.)
    else:
        return obj


def clear_cache(*, user: User) -> dict[str, bool]:
    require_admin_or_service(user)

    clear_all_caches()
    return {"success": True}


@cache_result("teams", ttl_seconds=CACHE_TTL)
def load_teams():
    teams = Team.find_all().run()
    return to_dicts(teams)


@invalidate_cache(keys=["teams"])
def create_team(*, name: str, user: User) -> dict[str, Any]:
    team = Team(
        name=name,
        owner_id=user.id,
        member_ids=[user.id],
    )
    team.insert()
    return to_dicts(team)


@cache_result("notion_tree", ttl_seconds=CACHE_TTL)
def load_notion():
    notion_data = Notion.find_all().run()
    return to_dicts(notion_data)


def load_notion_latest():
    all_notion = load_notion()
    if not all_notion:
        return None
    latest = max(all_notion, key=lambda x: x.get("submitted_at", ""))
    return latest


@invalidate_cache(keys=["notion_tree"])
def generate_and_store_notion_tree():
    tree = generate_tree()  # long-running blocking call
    notion = Notion(tree=tree)
    notion.insert()


def trigger_notion_refresh():
    def background_job():
        generate_and_store_notion_tree()

    threading.Thread(target=background_job, daemon=True).start()


@cache_result("playlists:index", ttl_seconds=CACHE_TTL)
def load_playlists():
    playlists = Playlist.find_all().run()
    return [
        {
            "_id": str(p.id),
            "name": p.name,
            "color": p.color,
            "owner_id": str(p.owner_id),
            "team_id": str(p.team_id),
            "playlist_id": p.playlist_id,
            "video_count": len(p.videos),
        }
        for p in playlists
    ]


def apply_training_date_logic(video: Dict[str, Any]) -> Dict[str, Any]:
    """
    Non-destructive enrichment:
    - preserve original date as publish_date
    - override date with training_date if present
    """
    enriched = dict(video)  # shallow copy to avoid mutation

    enriched["publish_date"] = enriched.get("date")
    enriched["date"] = enriched.get("training_date") or enriched.get("date")

    return enriched


@cache_result(lambda playlist_id: f"playlist:{playlist_id}", ttl_seconds=CACHE_TTL)
def load_playlist(playlist_id: str) -> Optional[Dict[str, Any]]:
    playlist = Playlist.find_one(Playlist.id == ObjectId(playlist_id)).run()
    if not playlist:
        return None

    data = to_dicts(playlist)

    # Apply enrichment to all videos
    videos = data.get("videos", [])
    enriched_videos = []

    for video in videos:
        enriched_video = apply_training_date_logic(video)
        enriched_videos.append(enriched_video)

    data["videos"] = enriched_videos

    return data


@invalidate_cache(keys=["playlists:index"])
def create_playlist(
    *,
    name: str,
    playlist_id: str,
    videos: list[dict[str, Any]],
    user: User,
) -> dict[str, Any]:
    playlist = Playlist(
        name=name,
        playlist_id=playlist_id,
        videos=[Video(**video) for video in videos],
        owner_id=user.id,
    )
    playlist.insert()
    return to_dicts(playlist)


@cache_result(lambda video_id: f"video:{video_id}", ttl_seconds=CACHE_TTL)
def load_video(video_id: str) -> Optional[Dict[str, Any]]:
    playlist = Playlist.find_one(Playlist.videos.video_id == video_id).run()
    if not playlist:
        return None

    playlist_data = load_playlist(str(playlist.id))  # reuse enriched version
    if not playlist_data:
        return None

    for video in playlist_data.get("videos", []):
        if video["video_id"] == video_id:
            v = dict(video)
            v["playlist_id"] = playlist_data["_id"]
            v["playlist_name"] = playlist_data["name"]
            v["playlist_color"] = playlist_data["color"]
            return v


@invalidate_cache(
    keys=lambda playlist_id, new_videos, **_: [
        f"playlist:{playlist_id}",
        "playlists:index",
        *[f"video:{video['video_id']}" for video in new_videos],
    ]
)
def add_video_to_playlist(
    *,
    playlist_id: str,
    new_videos: list[dict[str, Any]],
    user: User,
) -> dict[str, Any]:
    if not ObjectId.is_valid(playlist_id):
        raise ValueError("Invalid playlist ID")

    playlist = Playlist.find_one(Playlist.id == ObjectId(playlist_id)).run()

    if playlist is None:
        raise ValueError("Playlist not found")

    if not can_write_playlist(user, playlist):
        raise AuthError("Access denied")

    playlist.videos.extend(Video(**video) for video in new_videos)
    playlist.save()

    return to_dicts(playlist)


@invalidate_cache(
    keys=lambda playlist_id, video_ids, **_: [
        "playlists:index",
        f"playlist:{playlist_id}",
        "clips:index",
        *[f"video:{video_id}" for video_id in video_ids],
    ]
)
def delete_videos_from_playlist(
    *,
    playlist_id: str,
    video_ids: list[str],
    user: User,
) -> dict[str, Any]:
    if not ObjectId.is_valid(playlist_id):
        raise ValueError("Invalid playlist ID")

    playlist = Playlist.find_one(Playlist.id == ObjectId(playlist_id)).run()

    if playlist is None:
        raise ValueError("Playlist not found")

    if not can_write_playlist(user, playlist):
        raise AuthError("Access denied")

    ids_to_remove = set(video_ids)
    before_count = len(playlist.videos)

    playlist.videos = [video for video in playlist.videos if video.video_id not in ids_to_remove]

    removed_count = before_count - len(playlist.videos)

    if removed_count:
        playlist.save()

    return {
        "_id": str(playlist.id),
        "deleted_count": removed_count,
        "videos": to_dicts(playlist.videos),
    }


@invalidate_cache(
    keys=lambda playlist_id, updated_video, **_: [
        f"video:{updated_video['video_id']}",
        f"playlist:{playlist_id}",
        "clips:index",
    ]
)
def edit_video_in_playlist(
    *,
    playlist_id: str,
    updated_video: dict[str, Any],
    user: User,
) -> dict[str, Any]:
    if not ObjectId.is_valid(playlist_id):
        raise ValueError("Invalid playlist ID")

    playlist = Playlist.find_one(Playlist.id == ObjectId(playlist_id)).run()

    if playlist is None:
        raise ValueError("Playlist not found")

    if not can_write_playlist(user, playlist):
        raise AuthError("Access denied")

    updated_video = dict(updated_video)
    updated_video.pop("_id", None)

    updated_video_obj = Video(**updated_video)
    updated_video_id = updated_video_obj.video_id

    for index, video in enumerate(playlist.videos):
        if video.video_id != updated_video_id:
            continue

        updated_fields = video.model_dump()

        if "clips" in updated_video:
            updated_fields["clips"] = merge_embedded_docs(
                existing_docs=video.clips,
                updated_docs=updated_video_obj.clips,
                id_field="clip_id",
                doc_cls=Clip,
            )

        if "anchors" in updated_video:
            updated_fields["anchors"] = merge_embedded_docs(
                existing_docs=video.anchors,
                updated_docs=updated_video_obj.anchors,
                id_field="anchor_id",
                doc_cls=Anchor,
            )

        for key, value in updated_video.items():
            if key not in {"clips", "anchors"}:
                updated_fields[key] = value

        playlist.videos[index] = Video(**updated_fields)
        playlist.save()
        return to_dicts(playlist)

    raise ValueError("Video not found in playlist")


def merge_embedded_docs(
    *,
    existing_docs: list,
    updated_docs: list,
    id_field: str,
    doc_cls,
):
    """
    Generic merge helper for embedded docs (clips, anchors, etc.)
    """
    existing_map = {getattr(doc, id_field): doc.dict() for doc in existing_docs if getattr(doc, id_field, None)}

    merged_docs = []

    for doc in updated_docs:
        doc_dict = doc.dict()
        doc_id = doc_dict.get(id_field)

        if doc_id and doc_id in existing_map:
            merged = {**existing_map[doc_id], **doc_dict}
        else:
            if not doc_id:
                doc_dict[id_field] = str(uuid4())
            merged = doc_dict

        merged_docs.append(doc_cls(**merged))

    return merged_docs


@invalidate_cache(
    keys=lambda playlist_id, **_: [
        "playlists:index",
        f"playlist:{playlist_id}",
        *[
            f"video:{video.video_id}"
            for video in (Playlist.find_one(Playlist.id == ObjectId(playlist_id)).run().videos or [])
        ],
    ]
)
def update_playlist_color(
    *,
    playlist_id: str,
    color: str,
    user: User,
) -> dict[str, Any]:
    if not ObjectId.is_valid(playlist_id):
        raise ValueError("Invalid playlist ID")

    playlist = Playlist.find_one(Playlist.id == ObjectId(playlist_id)).run()

    if playlist is None:
        raise ValueError("Playlist not found")

    if not can_write_playlist(user, playlist):
        raise AuthError("Access denied")

    playlist.color = color
    playlist.save()

    return {
        "_id": str(playlist.id),
        "color": playlist.color,
    }


@invalidate_cache(keys=["cliplists"])
def create_cliplist(
    *,
    name: str,
    filters: dict[str, Any],
    user: User,
) -> dict[str, Any]:
    cliplist = Cliplist(
        name=name,
        filters=filters,
        owner_id=user.id,
    )
    cliplist.insert()
    return to_dicts(cliplist)


@cache_result("cliplists", ttl_seconds=CACHE_TTL)
def load_cliplists():
    cliplists = Cliplist.find_all().run()
    return to_dicts(cliplists)


def load_cliplist(cliplist_id: str):
    for cliplist in load_cliplists():
        if cliplist.get("_id") == cliplist_id:
            return cliplist
    return None


# TODO: this method is for non oauth login which we dont have currently
# if we need this, it should be updated to return user object similar to google_oauth
def login_user(email: str, password: str) -> dict[str, str] | bool:
    user = load_user_by_email(email)

    if user is None or not user.hashed_password:
        log.warning("Incorrect email or password", email=email)
        return False

    if not verify_password(password, user.hashed_password):
        log.warning("Incorrect email or password", email=email)
        return False

    token = create_access_token({"sub": str(user.id)})

    return {
        "access_token": token,
        "id": str(user.id),
        "email": str(user.email),
        "username": user.username,
    }


def load_feedback():
    feedbacks = Feedback.find_all().run()
    return to_dicts(feedbacks)


def create_feedback(feedback: str):
    feedb = Feedback(
        text=feedback,
    )
    feedb.insert()
    return to_dicts(feedb)


def _load_learnings():
    learnings = Learnings.find_all().run()
    return to_dicts(learnings)


def load_learnings(video_id: str):
    # filter first
    filtered = [_ for _ in _load_learnings() if _.get("video_id") == video_id]

    # TODO: refactor this logic as a decorator or utility function of adding user info
    # collect unique author_ids (stored as strings)
    author_ids = {_["author_id"] for _ in filtered if _.get("author_id")}

    # convert to ObjectIds
    object_ids = []
    for a in author_ids:
        try:
            object_ids.append(ObjectId(a))
        except Exception:
            pass  # skip invalid ids

    # fetch all users at once
    users = User.find({"_id": {"$in": object_ids}}).run()
    user_map = {str(u.id): u for u in users}

    # enrich
    for learning in filtered:
        user = user_map.get(learning["author_id"])
        if user:
            learning["author_name"] = user.username
    return filtered


def create_learning(
    *,
    text: str,
    user: User,
    video_id: str | None = None,
) -> dict[str, Any]:
    learning = Learnings(
        author_id=user.id,
        text=text,
        video_id=video_id,
    )
    learning.insert()
    return to_dicts(learning)


def update_learning(
    *,
    learning_id: str,
    text: str,
    user: User,
) -> dict[str, Any]:
    if not ObjectId.is_valid(learning_id):
        raise ValueError("Invalid learning ID")

    learning = Learnings.find_one(
        Learnings.id == ObjectId(learning_id),
        Learnings.author_id == user.id,
    ).run()

    if learning is None:
        raise ValueError("Learning not found or access denied")

    learning.text = text
    learning.updated_at = datetime.utcnow()
    learning.save()

    return to_dicts(learning)


def delete_learning(
    *,
    learning_id: str,
    user: User,
) -> bool:
    if not ObjectId.is_valid(learning_id):
        raise ValueError("Invalid learning ID")

    learning = Learnings.find_one(
        Learnings.id == ObjectId(learning_id),
        Learnings.author_id == user.id,
    ).run()

    if learning is None:
        raise ValueError("Learning not found or access denied")

    learning.delete()
    return True

import os
import threading
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List
from uuid import uuid4

import jwt
from bson import ObjectId
from bunnet import Document
from data.models import Anchor, Clip, Cliplist, Feedback, Learnings, Notion, Playlist, Team, User, Video
from dotenv import load_dotenv
from log import log
from nicegui import ui  # TODO: remove or use your own alert/logger
from passlib.context import CryptContext
from utils.cache import cache_result, invalidate_cache
from utils.notion import generate_tree

load_dotenv()
SECRET_KEY = os.getenv("JWT_SECRET")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

CACHE_TTL = int(os.getenv("CACHE_TTL", 604800))  # Cache TTL in seconds


@invalidate_cache(keys=["teams", "notion_tree", "playlists", "cliplists"])
def clear_cache() -> None:
    pass


def get_user_from_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload["sub"]
        user = User.find_one(User.id == ObjectId(user_id)).run()
        if not user:
            raise ValueError("User not found")
        return user
    except Exception as e:
        log.info(f"Token error: {e}")
        return None


class AuthError(Exception):
    pass


def with_user_from_token(fn):
    @wraps(fn)
    def wrapper(*args, token=None, **kwargs):
        if not token:
            raise AuthError("Missing token")

        user = get_user_from_token(token)
        if not user:
            raise AuthError("Invalid or expired token")

        # Inject user into kwargs
        return fn(*args, user=user, **kwargs)

    return wrapper


def to_dicts(obj: Any) -> Any:
    # Case 1: Bunnet or Pydantic document
    if isinstance(obj, Document):
        return to_dicts(obj.model_dump(mode="json", by_alias=True))

    # Case 2: ObjectId
    elif isinstance(obj, ObjectId):
        return str(obj)

    # Case 3: Dict (recursively process keys and values)
    elif isinstance(obj, dict):
        return {to_dicts(k): to_dicts(v) for k, v in obj.items()}

    # Case 4: List or tuple
    elif isinstance(obj, (list, tuple)):
        return [to_dicts(item) for item in obj]

    # Case 5: Anything else (primitive types, etc.)
    else:
        return obj


@cache_result("teams", ttl_seconds=CACHE_TTL)
def load_teams():
    log.info("Loading teams from database...")
    teams = Team.find_all().run()
    return to_dicts(teams)


@with_user_from_token
@invalidate_cache(keys=["teams"])
def create_team(name: str, user=None, **kwargs):
    team = Team(
        name=name,
        owner_id=user.id,  # inject user id
        member_ids=[user.id],  # inject user id
    )
    team.insert()
    return to_dicts(team)


@cache_result("notion_tree", ttl_seconds=CACHE_TTL)
def load_notion():
    log.info("Loading Notion data from database...")
    notion_data = Notion.find_all().run()
    return to_dicts(notion_data)


def load_notion_latest():
    log.info("Selecting latest Notion entry from loaded data...")
    all_notion = load_notion()
    if not all_notion:
        return None
    latest = max(all_notion, key=lambda x: x.get("submitted_at", ""))
    return latest


@invalidate_cache(keys=["notion_tree"])
def generate_and_store_notion_tree():
    log.info("Generating Notion tree...")
    tree = generate_tree()  # long-running blocking call
    notion = Notion(tree=tree)
    notion.insert()
    log.info("Saved Notion tree to DB and cleared cache.")


def trigger_notion_refresh():
    def background_job():
        generate_and_store_notion_tree()

    threading.Thread(target=background_job, daemon=True).start()
    ui.notify("Started Notion tree generation in background", type="info")


@cache_result("playlists", ttl_seconds=CACHE_TTL)
def load_playlists():
    log.info("Loading playlists from database...")
    playlists = Playlist.find_all().run()
    return to_dicts(playlists)


@with_user_from_token
@invalidate_cache(keys=["playlists"])
def create_playlist(name: str, playlist_id: str, videos: List[Dict[str, Any]], user=None, **kwargs):
    playlist = Playlist(
        name=name,
        playlist_id=playlist_id,
        videos=videos,
        owner_id=user.id,  # inject user id
    )
    playlist.insert()
    return to_dicts(playlist)


def can_write_playlist(user: User, playlist: Playlist) -> bool:
    if user.role == "service":
        return True
    return playlist.owner_id == user.id


@with_user_from_token
@invalidate_cache(keys=["playlists"])
def add_video_to_playlist(playlist_id: str, new_videos: List[Dict[str, Any]], user=None, **kwargs):

    playlist = Playlist.find_one(Playlist.id == ObjectId(playlist_id)).run()
    if not playlist or not can_write_playlist(user, playlist):
        raise AuthError("Playlist not found or access denied")

    playlist.videos.extend([Video(**video) for video in new_videos])
    playlist.save()
    return to_dicts(playlist)


# TODO: updates can be done by team members, not just owner
@with_user_from_token
@invalidate_cache(keys=["playlists"])
def edit_video_in_playlist(
    playlist_id: str,
    updated_video: Dict[str, Any],
    user=None,
    **kwargs,
):
    playlist = Playlist.find_one(
        Playlist.playlist_id == playlist_id,
        Playlist.owner_id == user.id,
    ).run()

    if not playlist:
        raise ValueError("Playlist not found or access denied")

    updated_video.pop("_id", None)
    updated_video_obj = Video(**updated_video)
    updated_video_id = updated_video_obj.video_id

    updated = False

    for i, video in enumerate(playlist.videos):
        if video.video_id != updated_video_id:
            continue

        updated_fields = video.dict()

        # --- CLIPS ---
        if "clips" in updated_video:
            merged_clips = merge_embedded_docs(
                existing_docs=video.clips,
                updated_docs=updated_video_obj.clips,
                id_field="clip_id",
                doc_cls=Clip,
            )
            updated_fields["clips"] = merged_clips

        # --- ANCHORS (NEW) ---
        if "anchors" in updated_video:
            merged_anchors = merge_embedded_docs(
                existing_docs=video.anchors,
                updated_docs=updated_video_obj.anchors,
                id_field="anchor_id",
                doc_cls=Anchor,
            )
            updated_fields["anchors"] = merged_anchors

        # --- ALL OTHER FIELDS ---
        for k, v in updated_video.items():
            if k not in {"clips", "anchors"}:
                updated_fields[k] = v

        playlist.videos[i] = Video(**updated_fields)
        updated = True
        break

    if not updated:
        raise ValueError("Video not found in playlist")

    playlist.save()
    return to_dicts(playlist)


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


@with_user_from_token
@invalidate_cache(keys=["playlists"])
def update_video_anchors(
    playlist_id: str,
    video_id: str,
    anchors: List[dict],
    user=None,
    **kwargs,
):
    playlist = Playlist.find_one(Playlist.id == ObjectId(playlist_id), Playlist.owner_id == user.id).run()

    if not playlist:
        raise ValueError("Playlist not found or access denied")

    def normalize_anchor_payload(a: dict) -> dict:
        if "id" in a and "anchor_id" not in a:
            a = {**a, "anchor_id": a.pop("id")}
        return a

    for i, video in enumerate(playlist.videos):
        if video.video_id != video_id:
            continue

        merged_anchors = merge_embedded_docs(
            existing_docs=video.anchors,
            updated_docs=[Anchor(**normalize_anchor_payload(a)) for a in anchors],
            id_field="anchor_id",
            doc_cls=Anchor,
        )

        updated_fields = video.dict()
        updated_fields["anchors"] = merged_anchors
        playlist.videos[i] = Video(**updated_fields)
        playlist.save()

        return to_dicts(playlist)

    raise ValueError("Video not found in playlist")


@with_user_from_token
@invalidate_cache(keys=["cliplists"])
def create_cliplist(name: str, filters: Dict[str, Any], user=None, **kwargs):
    cliplist = Cliplist(
        name=name,
        filters=filters,
        owner_id=user.id,  # inject user id
    )
    cliplist.insert()
    return to_dicts(cliplist)


@cache_result("cliplists", ttl_seconds=CACHE_TTL)
def load_cliplists():
    log.info("Loading cliplists from database...")
    cliplists = Cliplist.find_all().run()
    return to_dicts(cliplists)


def load_cliplist(cliplist_id: str):
    for cliplist in load_cliplists():
        if cliplist.get("_id") == cliplist_id:
            return cliplist
    return None


def get_or_create_user(email: str, username: str, oauth_provider: str, oauth_sub: str):
    user = load_user(email)
    if user:
        return user
    return create_user(email, username, oauth_provider, oauth_sub)


def create_user(email: str, username: str, oauth_provider: str, oauth_sub: str):
    user = User(
        username=username,
        email=email,
        oauth_provider=oauth_provider,
        oauth_sub=oauth_sub,
        hashed_password=None,
    )
    user.insert()
    return to_dicts(user)


def load_user(email: str):
    user = User.find_one(User.email == email).run()
    if user:
        return to_dicts(user)
    return None


def verify_password(plain_password, hashed):
    return pwd_context.verify(plain_password, hashed)


# TODO: combine with create_access_token
def create_service_token(service_user: User):
    return jwt.encode(
        {
            "sub": str(service_user.id),
            "role": "service",
            "exp": datetime.utcnow() + timedelta(days=30),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def login_user(email: str, password: str):
    user = load_user(email)
    if not user or not verify_password(password, user["hashed_password"]):
        log.info("Incorrect email or password")
        return False

    token = create_access_token({"sub": str(user["_id"])})
    return {
        "access_token": token,
        "id": str(user["_id"]),
        "email": user["email"],
        "username": user["username"],
    }


def load_feedback():
    log.info("Loading feedback from database...")
    feedbacks = Feedback.find_all().run()
    return to_dicts(feedbacks)


def create_feedback(feedback: str):
    feedb = Feedback(
        text=feedback,
    )
    feedb.insert()
    return to_dicts(feedb)


def _load_learnings():
    log.info("Loading learnings from database...")
    learnings = Learnings.find_all().run()
    return to_dicts(learnings)


def load_learnings(video_id: str):
    # filter first
    filtered = [_ for _ in _load_learnings() if _.get("video_id") == video_id]

    # TODO: refctor this logic as a decorator or utility function of adding user info
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


@with_user_from_token
def create_learning(author_id: str, text: str, video_id: str = None, clip_id: str = None, user=None, **kwargs):
    learning = Learnings(
        author_id=user.id,
        text=text,
        video_id=video_id,
        clip_id=clip_id,
    )
    learning.insert()
    return to_dicts(learning)


@with_user_from_token
def update_learning(learning_id: str, text: str, user=None, **kwargs):
    learning = Learnings.find_one(Learnings.id == ObjectId(learning_id), Learnings.author_id == user.id).run()
    if not learning:
        raise ValueError("Learning not found or access denied")
    learning.text = text
    learning.updated_at = datetime.utcnow()
    learning.save()
    return to_dicts(learning)


@with_user_from_token
def delete_learning(learning_id: str, user=None, **kwargs):
    learning = Learnings.find_one(Learnings.id == ObjectId(learning_id), Learnings.author_id == user.id).run()
    if not learning:
        raise ValueError("Learning not found or access denied")
    learning.delete()
    return True

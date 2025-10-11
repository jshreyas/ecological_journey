import os
import threading
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List
from uuid import uuid4

import jwt
from bson import ObjectId
from bunnet import Document
from data.models import Clip, Cliplist, Feedback, Learnings, Notion, Playlist, Team, Uploads, User, Video
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


def with_user_from_token(fn):
    @wraps(fn)
    def wrapper(*args, token=None, **kwargs):
        if not token:
            ui.notify("Missing token", type="negative")
            return None

        user = get_user_from_token(token)
        if not user:
            ui.notify("Invalid or expired token", type="negative")
            return None

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
def create_playlist(name: str, playlist_id: str, videos: List[Dict[str, Any]], source: str, user=None, **kwargs):
    playlist = Playlist(
        name=name,
        playlist_id=playlist_id,
        videos=videos,
        owner_id=user.id,  # inject user id
        source=source,  # e.g., "youtube" or "peertube"
    )
    playlist.insert()
    return to_dicts(playlist)


@with_user_from_token
@invalidate_cache(keys=["playlists"])
def add_video_to_playlist(playlist_id: str, new_videos: List[Dict[str, Any]], user=None, **kwargs):
    playlist = Playlist.find_one(Playlist.playlist_id == playlist_id, Playlist.owner_id == user.id).run()
    if not playlist:
        raise ValueError("Playlist not found or access denied")

    playlist.videos.extend([Video(**video) for video in new_videos])
    playlist.save()
    return to_dicts(playlist)


# TODO: updates can be done by team members, not just owner
@with_user_from_token
@invalidate_cache(keys=["playlists"])
def edit_video_in_playlist(playlist_id: str, updated_video: Dict[str, Any], user=None, **kwargs):
    playlist = Playlist.find_one(Playlist.playlist_id == playlist_id, Playlist.owner_id == user.id).run()

    if not playlist:
        raise ValueError("Playlist not found or access denied")

    updated_video_obj = Video(**updated_video)
    updated_video_id = updated_video_obj.video_id

    updated = False
    for i, video in enumerate(playlist.videos):
        if video.video_id == updated_video_id:
            # Step 1: Map existing clips by clip_id
            existing_clips = {clip.clip_id: clip.dict() for clip in video.clips}
            merged_clips = []

            for clip in updated_video_obj.clips:
                clip_dict = clip.dict()
                clip_id = clip_dict.get("clip_id")

                if clip_id and clip_id in existing_clips:
                    merged = {**existing_clips[clip_id], **clip_dict}
                else:
                    if not clip_id:
                        clip_dict["clip_id"] = str(uuid4())
                    merged = clip_dict

                merged_clips.append(Clip(**merged))

            # Step 2: Merge all fields properly
            updated_fields = video.dict()
            updated_fields.update(updated_video)
            updated_fields["clips"] = merged_clips

            # Step 3: Replace the video
            playlist.videos[i] = Video(**updated_fields)
            updated = True
            break

    if not updated:
        raise ValueError("Video not found in playlist")

    playlist.save()
    return to_dicts(playlist)


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


def create_uploads(upload_id: str, status: str, filename: str):
    uploads = Uploads(
        upload_id=upload_id,
        status=status,
        filename=filename,
    )
    uploads.insert()
    return to_dicts(uploads)


def update_uploads_status(upload_id: str, status: str):
    upload = Uploads.find_one(Uploads.upload_id == upload_id).run()
    if not upload:
        raise ValueError("Upload not found or access denied")
    upload.status = status
    upload.updated_at = datetime.utcnow()
    upload.save()
    return to_dicts(upload)


def update_uploads_logs(upload_id: str, logs: str):
    upload = Uploads.find_one(Uploads.upload_id == upload_id).run()
    if not upload:
        raise ValueError("Upload not found or access denied")
    upload.logs = logs
    upload.updated_at = datetime.utcnow()
    upload.save()
    return to_dicts(upload)


def load_uploads():
    upload = Uploads.find_all().run()
    return to_dicts(upload)


def load_upload(upload_id: str):
    upload = Uploads.find_one(Uploads.upload_id == upload_id).run()
    return to_dicts(upload)

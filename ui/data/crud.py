import os
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict

import jwt
from bson import ObjectId
from bunnet import Document
from data.models import Cliplist, Feedback, Notion, Playlist, Team, User
from dotenv import load_dotenv
from nicegui import ui  # TODO: remove or use your own alert/logger
from passlib.context import CryptContext
from utils.cache import cache_result, invalidate_cache

load_dotenv()
SECRET_KEY = os.getenv("JWT_SECRET")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def get_user_from_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload["sub"]
        user = User.find_one(User.id == ObjectId(user_id)).run()
        if not user:
            raise ValueError("User not found")
        return user
    except Exception as e:
        print(f"Token error: {e}")
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


@cache_result("teams", ttl_seconds=3600)
def load_teams():
    print("Loading teams from database...")
    teams = Team.find_all().run()
    return to_dicts(teams)


@cache_result("notion_tree", ttl_seconds=3600)
def load_notion():
    print("Loading Notion data from database...")
    notion_data = Notion.find_all().run()
    return to_dicts(notion_data)


def load_notion_latest():
    print("Selecting latest Notion entry from loaded data...")
    all_notion = load_notion()
    if not all_notion:
        return None
    latest = max(all_notion, key=lambda x: x.get("submitted_at", ""))
    return latest


@cache_result("playlists", ttl_seconds=3600)  # TODO: update ttl
def load_playlists():
    print("Loading playlists from database...")
    playlists = Playlist.find_all().run()
    return to_dicts(playlists)


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


@cache_result("cliplists", ttl_seconds=3600)
def load_cliplists():
    print("Loading cliplists from database...")
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
        print("Incorrect email or password")
        return False

    token = create_access_token({"sub": str(user["_id"])})
    return {
        "access_token": token,
        "id": str(user["_id"]),
        "email": user["email"],
        "username": user["username"],
    }


def load_feedback():
    print("Loading feedback from database...")
    feedbacks = Feedback.find_all().run()
    return to_dicts(feedbacks)


def create_feedback(feedback: str):
    feedb = Feedback(
        text=feedback,
    )
    feedb.insert()
    return to_dicts(feedb)

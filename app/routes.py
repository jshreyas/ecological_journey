# ---------------- app/routes.py ----------------
import os
from datetime import datetime, timedelta
import jwt
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import (
    HTTPAuthorizationCredentials,
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)
from fastapi.security.utils import get_authorization_scheme_param
from bson import ObjectId
from passlib.context import CryptContext

from .models import Playlist, Video, Clip
from .auth_models import Team, User, RegisterUser
from .db import db


SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed):
    return pwd_context.verify(plain_password, hashed)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Optional auth scheme
async def auth_scheme_optional(request: Request) -> HTTPAuthorizationCredentials | None:
    authorization: str | None = request.headers.get("Authorization")
    if not authorization:
        return None
    scheme, credentials = get_authorization_scheme_param(authorization)
    if scheme.lower() != "bearer":
        return None
    return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)


# APIRouter
router = APIRouter()


# Utility functions
def convert_objectid(data):
    if isinstance(data, list):
        return [convert_objectid(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_objectid(value) for key, value in data.items()}
    elif isinstance(data, ObjectId):
        return str(data)
    else:
        return data


async def get_playlist_by_name(name: str):
    return await db.playlists.find_one({"name": name})


async def get_all_playlists() -> list:
    playlists = await db.playlists.find().to_list(length=None)
    return playlists


async def get_video_by_id(playlist_name: str, video_id: str):
    return await db.playlists.find_one(
        {"name": playlist_name, "videos.video_id": video_id}
    )


async def insert_playlist(playlist: Playlist):
    await db.playlists.insert_one(playlist.dict())


async def insert_video(playlist_name: str, video: Video):
    await db.playlists.update_one(
        {"name": playlist_name}, {"$push": {"videos": video.dict()}}
    )


async def insert_clip(playlist_name: str, video_id: str, clip: Clip):
    await db.playlists.update_one(
        {"name": playlist_name, "videos.video_id": video_id},
        {"$push": {"videos.$.clips": clip.dict()}},
    )


# Routes
# auth
@router.post("/auth/register")
async def register(user_data: RegisterUser):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = get_password_hash(user_data.password)

    user = User(
        username=user_data.username, email=user_data.email, hashed_password=hashed
    )

    result = await db.users.insert_one(user.dict(by_alias=True))
    return {"id": str(result.inserted_id)}


@router.get("/users")
async def get_users(
    _: HTTPAuthorizationCredentials = Depends(auth_scheme_optional),
):
    projection = {"_id": 1, "username": 1, "team_ids": 1}
    users = await db.users.find({}, projection).to_list(length=None)
    return convert_objectid(users)


@router.post("/auth/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await db.users.find_one(
        {"email": form_data.username}
    )  # TODO: check username or email?
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token({"sub": str(user["_id"])})
    return {"access_token": token, "token_type": "bearer"}


# book keeping
@router.get("/teams")
async def get_teams(
    _: HTTPAuthorizationCredentials = Depends(auth_scheme_optional),
):
    teams = await db.teams.find().to_list(length=None)
    return convert_objectid(teams)


@router.post("/teams")
async def create_team(team: Team, user=Depends(get_current_user)):
    # Default owner_id to authenticated user
    team.owner_id = user["_id"]
    team.member_ids = [user["_id"]]
    result = await db.teams.insert_one(team.dict(by_alias=True))
    await db.users.update_one(
        {"_id": user["_id"]}, {"$push": {"team_ids": result.inserted_id}}
    )
    return {"id": str(result.inserted_id)}


@router.post("/teams/{team_id}/add_user/{user_id}")
async def add_user_to_team(team_id: str, user_id: str, user=Depends(get_current_user)):
    # TODO: Check if the user is already in the team? or doesnt matter
    team = await db.teams.find_one({"_id": ObjectId(team_id)})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if team["owner_id"] != user["_id"]:
        raise HTTPException(status_code=403, detail="Only owner can add members")

    await db.teams.update_one(
        {"_id": ObjectId(team_id)}, {"$addToSet": {"member_ids": ObjectId(user_id)}}
    )
    await db.users.update_one(
        {"_id": ObjectId(user_id)}, {"$addToSet": {"team_ids": ObjectId(team_id)}}
    )
    return {"msg": "User added to team"}


@router.get("/teams/{team_id}/members")
async def get_team_members(team_id: str, user=Depends(get_current_user)):
    team = await db.teams.find_one({"_id": ObjectId(team_id)})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if user["_id"] not in team["member_ids"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    members = await db.users.find({"_id": {"$in": team["member_ids"]}}).to_list(
        length=None
    )
    return [
        {"id": str(m["_id"]), "email": m["email"], "username": m["username"]}
        for m in members
    ]


# playlist
@router.get("/playlists")
async def get_playlists(
    _: HTTPAuthorizationCredentials = Depends(auth_scheme_optional),
):

    playlists = await get_all_playlists()
    return convert_objectid(playlists)


@router.post("/playlists")
async def create_playlist(playlist: Playlist, user=Depends(get_current_user)):
    existing_playlist = await get_playlist_by_name(playlist.name)
    if existing_playlist:
        raise HTTPException(status_code=400, detail="Playlist already exists.")

    playlist_dict = playlist.dict(by_alias=True)

    # Default owner_id to authenticated user
    if not playlist.owner_id:
        playlist_dict["owner_id"] = user["_id"]

    await db.playlists.insert_one(playlist_dict)
    return {"msg": "Playlist created successfully!"}


@router.get("/playlists/{playlist_name}")
async def get_playlist(
    playlist_name: str,
    _: HTTPAuthorizationCredentials = Depends(auth_scheme_optional),
):
    playlist = await get_playlist_by_name(playlist_name)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found.")
    return convert_objectid(playlist)


@router.post("/playlists/{playlist_name}/videos")
async def create_video(
    playlist_name: str, video: Video, user=Depends(get_current_user)
):

    playlist = await get_playlist_by_name(playlist_name)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found.")

    if not playlist["owner_id"] == user["_id"]:
        raise HTTPException(status_code=403, detail="Access denied to this playlist.")

    existing_video = await get_video_by_id(playlist_name, video.video_id)
    if existing_video:
        raise HTTPException(status_code=400, detail="Video already exists.")

    await insert_video(playlist_name, video)
    return {
        "msg": "Video added to playlist!"
    }  # TODO: return video object or something?


@router.post("/playlists/{playlist_name}/videos/{video_id}/clips")
async def create_clip(
    playlist_name: str, video_id: str, clip: Clip, user=Depends(get_current_user)
):
    playlist = await get_playlist_by_name(playlist_name)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found.")
    if not playlist["owner_id"] == user["_id"]:
        raise HTTPException(status_code=403, detail="Access denied to this playlist.")

    video = await get_video_by_id(playlist_name, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")

    await insert_clip(playlist_name, video_id, clip)
    return {"msg": "Clip added to video!"}


@router.put("/playlists/{playlist_name}/videos")
async def update_video(
    playlist_name: str, updated_video: Video, user=Depends(get_current_user)
):
    playlist = await get_playlist_by_name(playlist_name)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found.")

    # Extend access: allow playlist owner OR users from the team with access
    is_owner = playlist["owner_id"] == user["_id"]
    user_team_ids = set(user.get("team_ids", []))
    playlist_team_id = playlist.get("team_id")
    is_team_member = playlist_team_id in user_team_ids

    if not (is_owner or is_team_member):
        raise HTTPException(status_code=403, detail="Access denied to this playlist.")

    videos = playlist.get("videos", [])
    for i, video in enumerate(videos):
        if video["video_id"] == updated_video.video_id:
            updated_data = updated_video.dict()
            updated_data["video_id"] = video.get("video_id")
            updated_data["youtube_url"] = video.get("youtube_url")
            updated_data["date"] = video.get("date")
            updated_data["title"] = video.get("title")
            updated_data["duration_seconds"] = video.get("duration_seconds")
            updated_data["added_date"] = video.get("added_date")
            videos[i] = updated_data

            await db.playlists.update_one(
                {"name": playlist_name}, {"$set": {"videos": videos}}
            )
            return {"msg": "Video updated successfully!"}

    raise HTTPException(status_code=404, detail="Video not found in playlist.")


@router.put("/playlists/{playlist_name}/assign-team")
async def assign_playlist_to_team(
    playlist_name: str, team_id: str, user=Depends(get_current_user)
):
    user_id = user["_id"]

    # 1. Check if playlist exists and is owned by the user
    playlist = await get_playlist_by_name(playlist_name)
    # await db.playlists.find_one({"_id": ObjectId(playlist_id), "owner_id": user_id})
    if not playlist:
        raise HTTPException(
            status_code=404, detail="Playlist not found or not owned by user."
        )
    if not playlist["owner_id"] == user_id:
        raise HTTPException(status_code=403, detail="Access denied to this playlist.")

    # 2. Check if the team exists and user is a member
    team = await db.teams.find_one({"_id": ObjectId(team_id), "member_ids": user_id})
    if not team:
        raise HTTPException(status_code=403, detail="User not a member of this team.")

    # 3. Assign playlist to team
    await db.playlists.update_one(
        {"name": playlist_name}, {"$set": {"team_id": ObjectId(team_id)}}
    )

    return {"msg": "Playlist assigned to team successfully."}

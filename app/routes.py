# ---------------- app/routes.py ----------------
from fastapi import APIRouter, HTTPException, Depends, Request
from .models import Playlist, Video, Clip
from .auth_models import Team, User, RegisterUser
from typing import List
from bson import ObjectId
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
import os
from .db import db
from passlib.context import CryptContext


from fastapi.security.utils import get_authorization_scheme_param
from datetime import datetime, timedelta


SECRET_KEY = os.getenv("JWT_SECRET", "supersecret")
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

##
JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")
auth_scheme = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        return payload  # payload contains user_id and possibly team_ids
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Optional auth scheme
async def auth_scheme_optional(request: Request) -> HTTPAuthorizationCredentials | None:
    authorization: str = request.headers.get("Authorization")
    if not authorization:
        return None
    scheme, credentials = get_authorization_scheme_param(authorization)
    if scheme.lower() != "bearer":
        return None
    return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)

# Safe token decoder
async def try_decode_token(credentials: HTTPAuthorizationCredentials | None) -> dict | None:
    if not credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


router = APIRouter()

# Utility functions

def convert_objectid(data):
    if isinstance(data, list):
        return [convert_objectid(item) for item in data]
    elif isinstance(data, dict):
        return {
            key: convert_objectid(value)
            for key, value in data.items()
        }
    elif isinstance(data, ObjectId):
        return str(data)
    else:
        return data


async def get_playlist_by_name(name: str):
    return await db.playlists.find_one({"name": name})

async def get_all_playlists() -> list:
    # if user_id:
    #     query = {
    #         "$or": [
    #             {"owner": user_id},
    #             {"team_id": {"$in": team_ids}},
    #             {"public": True}
    #         ]
    #     }
    # else:
    #     query = {"public": True}
    query = {}
    playlists = await db.playlists.find(query).to_list(length=None)
    return playlists

async def get_video_by_id(playlist_name: str, video_id: str):
    return await db.playlists.find_one({"name": playlist_name, "videos.video_id": video_id})


async def insert_playlist(playlist: Playlist):
    await db.playlists.insert_one(playlist.dict())

async def insert_video(playlist_name: str, video: Video):
    await db.playlists.update_one(
        {"name": playlist_name},
        {"$push": {"videos": video.dict()}}
    )

async def insert_clip(playlist_name: str, video_id: str, clip: Clip):
    await db.playlists.update_one(
        {"name": playlist_name, "videos.video_id": video_id},
        {"$push": {"videos.$.clips": clip.dict()}}
    )

def can_edit_playlist(playlist, user_id: str, team_ids: List[str]):
    return playlist["user_id"] == user_id or playlist.get("team_id") in team_ids

def can_view_playlist(playlist):
    # Everyone can view (public)
    return True


def check_playlist_access(playlist, user_id, team_ids):
    if playlist["user_id"] == user_id or playlist["team_id"] in team_ids:
        return True
    raise HTTPException(status_code=403, detail="Access denied to this playlist.")

# Routes
# auth
@router.post("/auth/register")
async def register(user_data: RegisterUser):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed = get_password_hash(user_data.password)
    
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed
    )
    
    result = await db.users.insert_one(user.dict(by_alias=True))
    return {"id": str(result.inserted_id)}


@router.post("/auth/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await db.users.find_one({"email": form_data.username}) #TODO: check username or email?
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token({"sub": str(user["_id"])})
    return {"access_token": token, "token_type": "bearer"}

# book keeping
@router.post("/teams")
async def create_team(team: Team, user=Depends(get_current_user)):
    # Default owner_id to authenticated user
    team.owner_id = user["_id"]
    team.member_ids = [user["_id"]]
    result = await db.teams.insert_one(team.dict(by_alias=True))
    await db.users.update_one({"_id": user["_id"]}, {"$push": {"team_ids": result.inserted_id}})
    return {"id": str(result.inserted_id)}

@router.post("/teams/{team_id}/add_user/{user_id}")
async def add_user_to_team(team_id: str, user_id: str, user=Depends(get_current_user)):
    #TODO: Check if the user is already in the team? or doesnt matter
    team = await db.teams.find_one({"_id": ObjectId(team_id)})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if team["owner_id"] != user["_id"]:
        raise HTTPException(status_code=403, detail="Only owner can add members")

    await db.teams.update_one({"_id": ObjectId(team_id)}, {"$addToSet": {"member_ids": ObjectId(user_id)}})
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$addToSet": {"team_ids": ObjectId(team_id)}})
    return {"msg": "User added to team"}

@router.get("/teams/{team_id}/members")
async def get_team_members(team_id: str, user=Depends(get_current_user)):
    team = await db.teams.find_one({"_id": ObjectId(team_id)})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if user["_id"] not in team["member_ids"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    members = await db.users.find({"_id": {"$in": team["member_ids"]}}).to_list(length=None)
    return [{"id": str(m["_id"]), "email": m["email"], "username": m["username"]} for m in members]


# playlist
@router.get("/playlists")
async def get_playlists(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme_optional)):

    # user = await try_decode_token(credentials) #TODO: do i need this if read access is for everyone?
    playlists = await get_all_playlists()
    return convert_objectid(playlists)

@router.post("/playlists")
async def create_playlist(playlist: Playlist, user=Depends(verify_token)):
    existing_playlist = await get_playlist_by_name(playlist.name)
    if existing_playlist:
        raise HTTPException(status_code=400, detail="Playlist already exists.")

    playlist_dict = playlist.dict(by_alias=True)

    # Default owner_id to authenticated user
    if not playlist.owner_id:
        playlist_dict["owner_id"] = ObjectId(user["sub"]) #TODO: test this?

    # Default owner_type to "user" (already handled by model default)

    await db.playlists.insert_one(playlist_dict)
    return {"msg": "Playlist created successfully!"}

@router.get("/playlists/{playlist_name}")
async def get_playlist(playlist_name: str, credentials: HTTPAuthorizationCredentials = Depends(auth_scheme_optional)):
    playlist = await get_playlist_by_name(playlist_name)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found.")
    return convert_objectid(playlist)

@router.post("/playlists/{playlist_name}/videos")
async def create_video(playlist_name: str, video: Video, user=Depends(get_current_user)): # credentials: HTTPAuthorizationCredentials = Depends(auth_scheme_optional)

    playlist = await get_playlist_by_name(playlist_name)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found.")

    if not playlist["owner_id"] == user["_id"]:
        raise HTTPException(status_code=403, detail="Access denied to this playlist.")

    existing_video = await get_video_by_id(playlist_name, video.video_id)
    if existing_video:
        raise HTTPException(status_code=400, detail="Video already exists.")

    await insert_video(playlist_name, video)
    return {"msg": "Video added to playlist!"} #TODO: return video object or something?

@router.post("/playlists/{playlist_name}/videos/{video_id}/clips")
async def create_clip(playlist_name: str, video_id: str, clip: Clip, user=Depends(get_current_user)):
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
async def update_video(playlist_name: str, updated_video: Video, user=Depends(get_current_user)):
    playlist = await get_playlist_by_name(playlist_name)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found.")
    # check_playlist_access(playlist, user["user_id"], user.get("team_ids", []))
    if not playlist["owner_id"] == user["_id"]: #TODO: check if the user is in the team mapped to playlist
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
                {"name": playlist_name},
                {"$set": {"videos": videos}}
            )
            return {"msg": "Video updated successfully!"}

    raise HTTPException(status_code=404, detail="Video not found in playlist.")

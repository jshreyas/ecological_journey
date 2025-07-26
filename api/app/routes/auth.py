import os
from datetime import datetime, timedelta

import jwt
from authlib.integrations.starlette_client import OAuth, OAuthError
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.security.utils import get_authorization_scheme_param
from passlib.context import CryptContext

from ..auth_models import RegisterUser, User
from ..db import db

load_dotenv()

router = APIRouter()
SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
FRONTEND_URL = os.getenv("FRONTEND_URL")
BACKEND_REDIRECT_URL = os.getenv("BACKEND_REDIRECT_URL")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


oauth = OAuth()
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    client_kwargs={"scope": "openid email profile"},
    redirect_uri=f"{BACKEND_REDIRECT_URL}/auth/google/callback",
)


async def auth_scheme_optional(request: Request) -> HTTPAuthorizationCredentials | None:
    authorization: str | None = request.headers.get("Authorization")
    if not authorization:
        return None
    scheme, credentials = get_authorization_scheme_param(authorization)
    if scheme.lower() != "bearer":
        return None

    # Not needed id GET requests dont pass a token
    # Minimal validation: suppress obviously invalid tokens (e.g. None or empty strings)
    # because this is an optional scheme and should only be used for GET requests
    if not credentials or not isinstance(credentials, str) or len(credentials) < 10:
        # TODO: consider logging invalid tokens here for later analysis
        return None

    # Just return token as-is, defer full validation elsewhere
    return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed):
    return pwd_context.verify(plain_password, hashed)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
):  # This line enables Swagger auth
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_or_create_user(email: str, username: str, oauth_provider: str, oauth_sub: str):
    user = await db.users.find_one(
        {"$or": [{"email": email}, {"oauth_provider": oauth_provider, "oauth_sub": oauth_sub}]}
    )
    if user:
        return user
    new_user = {
        "username": username,
        "email": email,
        "oauth_provider": oauth_provider,
        "oauth_sub": oauth_sub,
        "hashed_password": None,
    }
    result = await db.users.insert_one(new_user)
    new_user["_id"] = result.inserted_id
    return new_user


# TODO: Verify email before allowing registration
@router.post("/auth/register")
async def register(user_data: RegisterUser):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = get_password_hash(user_data.password)
    user = User(username=user_data.username, email=user_data.email, hashed_password=hashed)
    result = await db.users.insert_one(user.dict(by_alias=True))
    token = create_access_token({"sub": str(result.inserted_id)})
    return {
        "access_token": token,
        "id": str(result.inserted_id),
        "email": user.email,
        "username": user.username,
    }


@router.post("/auth/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await db.users.find_one({"email": form_data.username})  # TODO: check username or email?
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token({"sub": str(user["_id"])})
    return {
        "access_token": token,
        "id": str(user["_id"]),
        "email": user["email"],
        "username": user["username"],
    }


@router.get("/auth/google/login")
async def google_login(request: Request):
    post_login_path = request.query_params.get("post_login_path")
    redirect_uri = f"{BACKEND_REDIRECT_URL}/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri, state=post_login_path)


@router.get("/auth/google/callback")
async def google_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        resp = await oauth.google.get("https://openidconnect.googleapis.com/v1/userinfo", token=token)
        userinfo = resp.json()
    except OAuthError:
        print("OAuth error:", OAuthError)
        return RedirectResponse(url=f"{FRONTEND_URL}/?error=oauth")
    # TODO: Handle token expiration and refresh
    request.session["user"] = userinfo
    user = await get_or_create_user(userinfo["email"], userinfo["name"], "google", userinfo["sub"])
    jwt_token = create_access_token({"sub": str(user["_id"])})
    post_login_path = request.query_params.get("state")
    return RedirectResponse(
        url=f'{FRONTEND_URL}/oauth?token={jwt_token}&username={userinfo["name"]}'
        f'&id={str(user["_id"])}&post_login_path={post_login_path}'
    )

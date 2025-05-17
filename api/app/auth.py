# ---------------- app/auth.py ----------------
import os
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from fastapi import Request
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from fastapi.security.utils import get_authorization_scheme_param
from dotenv import load_dotenv

load_dotenv()

auth_scheme = HTTPBearer()
SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed):
    return pwd_context.verify(plain_password, hashed)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# Optional auth scheme
async def auth_scheme_optional(request: Request) -> HTTPAuthorizationCredentials | None:
    authorization: str | None = request.headers.get("Authorization")
    if not authorization:
        return None
    scheme, credentials = get_authorization_scheme_param(authorization)
    if scheme.lower() != "bearer":
        return None

    # Minimal validation: suppress obviously invalid tokens (e.g. None or empty strings)
    # because this is an optional scheme and should only be used for GET requests
    if not credentials or not isinstance(credentials, str) or len(credentials) < 10:
        # TODO: consider logging invalid tokens here for later analysis
        return None

    # Just return token as-is, defer full validation elsewhere
    return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)

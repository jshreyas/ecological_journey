import os
from datetime import datetime, timedelta
from typing import Annotated, Any

import jwt
from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from ui.data.models import User
from ui.log import log

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7


class AuthError(Exception):
    """Raised when an application request has no valid authenticated user."""

    pass


def get_user_from_token(token: str) -> User | None:
    """
    Return the canonical User represented by an application JWT.

    This is deliberately the only place that converts JWT -> user document.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = payload.get("sub")
        if not isinstance(user_id, str) or not ObjectId.is_valid(user_id):
            return None

        return User.find_one(User.id == ObjectId(user_id)).run()

    except InvalidTokenError as exc:
        log.warning("Invalid application JWT", error=str(exc))
        return None
    except Exception:
        log.exception("Could not resolve user from application JWT")
        return None


def require_user_from_token(token: str | None) -> User:
    """
    Resolve a token to User or raise a domain-level authentication exception.

    Use this for non-FastAPI entry points that genuinely only possess a token.
    """
    if not token:
        raise AuthError("Authentication required")

    user = get_user_from_token(token)
    if user is None:
        raise AuthError("Invalid, expired, or revoked authentication token")

    return user


def create_access_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="JWTBearer",
)


def require_api_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> User:
    """
    FastAPI boundary dependency:
    Authorization: Bearer <application-JWT> -> User.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_from_token(credentials.credentials)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user

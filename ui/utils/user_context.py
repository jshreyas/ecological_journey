from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from nicegui import app
from structlog.contextvars import bind_contextvars

from ui.data.auth import AuthError, require_user_from_token
from ui.data.models import User

P = ParamSpec("P")
R = TypeVar("R")


def get_current_user() -> User | None:
    """Return the current NiceGUI session user, or None for anonymous visitors."""
    session = app.storage.user

    if not session.get("authenticated"):
        return None

    token = session.get("token")
    if not isinstance(token, str) or not token:
        return None

    try:
        return require_user_from_token(token)
    except AuthError:
        session.clear()
        session["authenticated"] = False
        return None


def require_current_user() -> User:
    """Return the authenticated NiceGUI user or fail explicitly."""
    user = get_current_user()

    if user is None:
        raise AuthError("Please sign in to continue")

    return user


def with_user_context(page_func: Callable[P, R]) -> Callable[P, R]:
    @wraps(page_func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        user = get_current_user()

        bind_contextvars(
            user_id=str(user.id) if user else None,
            username=user.username if user else "anonymous",
            role=user.role if user else None,
        )

        return page_func(user, *args, **kwargs)

    return wrapper

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from nicegui import app
from structlog.contextvars import bind_contextvars

from ui.data.crud import get_user_from_token
from ui.data.models import User

P = ParamSpec("P")
R = TypeVar("R")


def get_current_user() -> User | None:
    """
    Resolve the current NiceGUI browser session into the canonical User model.

    app.storage.user contains only JSON-safe session metadata; this function
    turns its application JWT into a database User document.
    """
    session = app.storage.user
    token = session.get("token")

    if not session.get("authenticated") or not token:
        return None

    user = get_user_from_token(token)

    if user is None:
        # Token is stale, invalid, expired, or its user was deleted.
        # Do not leave the browser appearing authenticated.
        session.clear()
        session["authenticated"] = False
        return None

    return user


def with_user_context(page_func: Callable[P, R]) -> Callable[P, R]:
    """
    Inject `user: User | None` as the first page-function argument.

    Page functions receive the real database User document, never a parallel
    dataclass or raw app.storage.user dictionary.
    """

    @wraps(page_func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        user = get_current_user()

        bind_contextvars(
            user_id=str(user.id) if user else None,
            username=user.username if user else "anonymous",
            email=str(user.email) if user else None,
            role=user.role if user else None,
        )

        return page_func(user, *args, **kwargs)

    return wrapper

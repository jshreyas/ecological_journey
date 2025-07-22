from dataclasses import dataclass
from functools import wraps
from typing import Callable

from nicegui import app


@dataclass
class User:
    username: str
    token: str
    id: str


def with_user_context(page_func: Callable):
    @wraps(page_func)
    def wrapper(*args, **kwargs):
        user = None
        user_data = getattr(app.storage, "user", None)
        if user_data and user_data.get("user") and user_data.get("token") and user_data.get("id"):
            user = User(
                username=user_data.get("user"),
                token=user_data.get("token"),
                id=user_data.get("id"),
            )
        return page_func(user, *args, **kwargs)

    return wrapper

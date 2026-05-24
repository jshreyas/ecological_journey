from dataclasses import dataclass
from functools import wraps
from typing import Callable

from nicegui import app
from structlog.contextvars import bind_contextvars


# TODO: This is duplication of the User class in ui/data/models.py.
@dataclass
class User:
    username: str
    token: str
    id: str
    email: str


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
                email=user_data["user_info"]["email"],
            )
            bind_contextvars(user=user_data.get("user"))
        else:
            bind_contextvars(user="John Doe")
        return page_func(user, *args, **kwargs)

    return wrapper

from unittest.mock import Mock

import jwt
import pytest
from bson import ObjectId
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from ui.data import auth as auth_module
from ui.data.auth import AuthError


def test_get_user_from_token_resolves_subject_to_user(monkeypatch):
    user_id = ObjectId()
    user = Mock(id=user_id)
    query = Mock()
    query.run.return_value = user
    find_one = Mock(return_value=query)
    monkeypatch.setattr(auth_module, "SECRET_KEY", "unit-test-secret")
    monkeypatch.setattr(auth_module.User, "find_one", find_one)
    token = jwt.encode({"sub": str(user_id)}, "unit-test-secret", algorithm=auth_module.ALGORITHM)

    result = auth_module.get_user_from_token(token)

    assert result is user
    find_one.assert_called_once()


@pytest.mark.parametrize("token", ["not-a-jwt", ""])
def test_require_user_from_token_rejects_invalid_tokens(token):
    with pytest.raises(AuthError):
        auth_module.require_user_from_token(token)


def test_require_api_user_rejects_missing_bearer_credentials():
    with pytest.raises(HTTPException) as error:
        auth_module.require_api_user(None)

    assert error.value.status_code == 401
    assert error.value.headers["WWW-Authenticate"] == "Bearer"


def test_require_api_user_returns_resolved_user(monkeypatch):
    user = Mock()
    monkeypatch.setattr(auth_module, "get_user_from_token", Mock(return_value=user))

    result = auth_module.require_api_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token"))

    assert result is user

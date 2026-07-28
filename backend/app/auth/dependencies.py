import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.auth.security import decode_access_token
from backend.app.auth.users_repository import get_user_by_id

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme)) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session. Please log in again.")

    user = get_user_by_id(int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session. Please log in again.")

    return user


def get_optional_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme)) -> dict | None:
    """Like get_current_user, but returns None instead of 401 when there's no
    (or an invalid) token - for routes that serve both logged-out and
    logged-in callers, where only the logged-in path needs the identity.
    """
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        return None
    return get_user_by_id(int(payload["sub"]))


def require_role(role: str):
    def _check(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] != role:
            raise HTTPException(status_code=403, detail=f"This action requires a {role} account.")
        return user

    return _check

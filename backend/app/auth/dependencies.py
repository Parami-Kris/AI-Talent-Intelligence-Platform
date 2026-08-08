import time

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.auth.security import decode_access_token
from backend.app.auth.users_repository import get_user_by_id

_bearer_scheme = HTTPBearer(auto_error=False)

# Every route except /auth/me only ever reads id/role off current_user, both
# of which are already signed into the JWT - re-fetching the full user row on
# every request cost a full extra TiDB round trip for no benefit on those
# routes. This cache lets a verified (id -> role) fact be trusted for a
# bounded window instead of either re-hitting TiDB every request or trusting
# the JWT blindly for its full 7-day life with no revocation check at all -
# a deleted/deactivated account stops working within this TTL, not up to 7
# days later. Single-process in-memory cache is fine here: the Space runs one
# Uvicorn worker (see Dockerfile CMD), so there's no cross-process staleness
# to worry about, and it resets naturally on redeploy/restart.
_ROLE_CACHE_TTL_SECONDS = 300
_role_cache: dict[int, tuple[str, float]] = {}


def _verified_claims(credentials: HTTPAuthorizationCredentials) -> dict:
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session. Please log in again.")

    user_id = int(payload["sub"])
    now = time.monotonic()
    cached = _role_cache.get(user_id)
    if cached and cached[1] > now:
        return {"id": user_id, "role": cached[0]}

    user = get_user_by_id(user_id)
    if user is None:
        _role_cache.pop(user_id, None)
        raise HTTPException(status_code=401, detail="Invalid or expired session. Please log in again.")

    _role_cache[user_id] = (user["role"], now + _ROLE_CACHE_TTL_SECONDS)
    return {"id": user_id, "role": user["role"]}


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme)) -> dict:
    """Full DB-backed lookup, always fresh - only /auth/me needs this, since
    it's the only route returning profile fields (email/display_name) the
    JWT doesn't carry. Everything else should use get_current_claims/
    get_optional_user/require_role, which are cached (see _verified_claims).
    """
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


def get_current_claims(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme)) -> dict:
    """Like get_current_user, but returns only {"id", "role"} and is cached -
    use this (directly or via require_role) unless the route genuinely needs
    email/display_name.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return _verified_claims(credentials)


def get_optional_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme)) -> dict | None:
    """Like get_current_claims, but returns None instead of 401 when there's
    no (or an invalid) token - for routes that serve both logged-out and
    logged-in callers, where only the logged-in path needs the identity.
    """
    if credentials is None:
        return None
    try:
        return _verified_claims(credentials)
    except HTTPException:
        return None


def require_role(role: str):
    def _check(user: dict = Depends(get_current_claims)) -> dict:
        if user["role"] != role:
            raise HTTPException(status_code=403, detail=f"This action requires a {role} account.")
        return user

    return _check

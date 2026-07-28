import jwt
import pytest

from backend.app.auth.security import create_access_token, decode_access_token, hash_password, verify_password


def test_hash_password_verifies_correct_password():
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", hashed) is True


def test_hash_password_rejects_wrong_password():
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("wrong-password", hashed) is False


def test_create_and_decode_access_token_round_trips(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    token = create_access_token(user_id=42, role="recruiter")
    payload = decode_access_token(token)

    assert payload["sub"] == "42"
    assert payload["role"] == "recruiter"


def test_decode_access_token_rejects_token_signed_with_different_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    token = create_access_token(user_id=42, role="recruiter")

    monkeypatch.setenv("JWT_SECRET", "a-different-secret")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token)

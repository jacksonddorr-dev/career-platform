import base64
import hashlib
import hmac
import secrets

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import AdminUser


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return base64.urlsafe_b64encode(salt + digest).decode()


def verify_password(password: str, encoded: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(encoded.encode())
        return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", password.encode(), raw[:16], 120_000), raw[16:])
    except (ValueError, TypeError):
        return False


def make_session(username: str) -> str:
    payload = base64.urlsafe_b64encode(username.encode()).decode().rstrip("=")
    signature = hmac.new(get_settings().session_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def session_username(cookie: str | None) -> str | None:
    if not cookie or "." not in cookie:
        return None
    payload, signature = cookie.split(".", 1)
    expected = hmac.new(get_settings().session_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        return base64.urlsafe_b64decode(payload + "==").decode()
    except (ValueError, UnicodeDecodeError):
        return None


def require_admin(session: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> AdminUser:
    username = session_username(session)
    try:
        user = db.query(AdminUser).filter_by(username=username).first() if username else None
    except Exception:
        user = next((item for item in db.identity_map.values()
                     if isinstance(item, AdminUser) and item.username == username), None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user

"""Authentication and session helpers."""

import hashlib
import os
import http.cookies as Cookie
from urllib.parse import parse_qs

from . import db

SESSIONS = {}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    # Normalize stored hash to lowercase in case MySQL returns uppercase
    return hash_password(password) == (hashed or "").lower()


def create_session(user):
    session_id = os.urandom(16).hex()
    SESSIONS[session_id] = {
        "user_id": user["user_id"],
        "email": user["email"],
        "role": user["role"],
    }
    return session_id


def get_session(environ):
    cookie_header = environ.get("HTTP_COOKIE", "")
    if not cookie_header:
        return None, None

    cookie = Cookie.SimpleCookie()
    cookie.load(cookie_header)
    session_cookie = cookie.get("session_id")
    if session_cookie is None:
        return None, None

    session_id = session_cookie.value
    return session_id, SESSIONS.get(session_id)


def destroy_session(environ, headers):
    cookie_header = environ.get("HTTP_COOKIE", "")
    cookie = Cookie.SimpleCookie()
    if cookie_header:
        cookie.load(cookie_header)
    cookie["session_id"] = ""
    cookie["session_id"]["path"] = "/"
    cookie["session_id"]["max-age"] = 0
    headers.append(("Set-Cookie", cookie.output(header="")))


def parse_post(environ):
    try:
        size = int(environ.get("CONTENT_LENGTH", 0))
    except (ValueError, TypeError):
        size = 0
    body = environ["wsgi.input"].read(size).decode("utf-8")
    return {k: v[0] for k, v in parse_qs(body).items()}


def login_user(email, password):
    sql = "SELECT * FROM users WHERE email=%s AND is_active=1"
    user = db.query_one(sql, (email,))
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def register_customer(full_name, email, phone, address, city, password):
    existing = db.query_one("SELECT user_id FROM users WHERE email=%s", (email,))
    if existing:
        return None, "Email already registered"

    pwd_hash = hash_password(password)
    user_id = db.execute(
        "INSERT INTO users (email, password_hash, role) VALUES (%s,%s,'CUSTOMER')",
        (email, pwd_hash),
    )
    customer_id = db.execute(
        "INSERT INTO customers (user_id, full_name, phone, address, city) VALUES (%s,%s,%s,%s,%s)",
        (user_id, full_name, phone, address, city),
    )
    return customer_id, None

"""
Vinverse auth API — Google sign-in for Intelligence Fellows.

Mount in main.py:

    from auth_google import router as auth_router
    app.include_router(auth_router)
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel, EmailStr, Field

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALG = "HS256"
JWT_HOURS = int(os.getenv("JWT_HOURS", "24"))
AUTO_APPROVE = os.getenv("AUTH_AUTO_APPROVE", "false").lower() == "true"
ALLOWED_EMAILS = {
    email.strip().lower()
    for email in os.getenv("ALLOWED_EMAILS", "").split(",")
    if email.strip()
}
STORE_PATH = Path(os.getenv("AUTH_STORE_PATH", "/tmp/vinverse_auth_store.json"))

router = APIRouter(prefix="/api/auth", tags=["auth"])


class GoogleLoginBody(BaseModel):
    credential: str = Field(..., description="Google ID token from GIS / OAuth")


class RegisterBody(BaseModel):
    name: str
    email: EmailStr
    phone: str = ""


def _load_store() -> dict[str, Any]:
    if STORE_PATH.exists():
        return json.loads(STORE_PATH.read_text())
    return {"pending": [], "approved": sorted(ALLOWED_EMAILS)}


def _save_store(store: dict[str, Any]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(store, indent=2))


def _is_approved(email: str) -> bool:
    email = email.lower()
    if AUTO_APPROVE:
        return True
    if email in ALLOWED_EMAILS:
        return True
    store = _load_store()
    return email in {item.lower() for item in store.get("approved", [])}


def _issue_token(user: dict[str, Any]) -> str:
    now = int(time.time())
    payload = {
        "sub": user["sub"],
        "email": user["email"],
        "name": user.get("name"),
        "role": user.get("role", "intelligence_fellow"),
        "iat": now,
        "exp": now + JWT_HOURS * 3600,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def _verify_google_token(credential: str) -> dict[str, Any]:
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_CLIENT_ID is not set on the server.",
        )
    try:
        info = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Google credential: {exc}") from exc

    if info.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(status_code=401, detail="Invalid token issuer.")
    if not info.get("email"):
        raise HTTPException(status_code=401, detail="Google account has no email.")
    if info.get("email_verified") is False:
        raise HTTPException(status_code=401, detail="Google email is not verified.")
    return info


def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    token = authorization.split(" ", 1)[1].strip()
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Session expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid session token.") from exc


@router.post("/google")
def google_login(body: GoogleLoginBody) -> dict[str, Any]:
    info = _verify_google_token(body.credential)
    email = info["email"].lower()

    if not _is_approved(email):
        raise HTTPException(
            status_code=403,
            detail="This Google account is not approved yet. Register first and wait for admin approval.",
        )

    user = {
        "name": info.get("name") or email.split("@")[0],
        "email": email,
        "picture": info.get("picture", ""),
        "sub": info.get("sub"),
        "provider": "google",
        "role": "intelligence_fellow",
    }
    token = _issue_token(user)
    return {"token": token, "user": user}


@router.post("/register")
def register(body: RegisterBody) -> dict[str, Any]:
    store = _load_store()
    email = body.email.lower()
    pending = store.setdefault("pending", [])
    if any(item.get("email") == email for item in pending) or email in store.get("approved", []):
        return {"status": "pending", "message": "This email is already on file."}

    pending.append(
        {
            "name": body.name,
            "email": email,
            "phone": body.phone,
            "requestedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": "pending",
        }
    )
    _save_store(store)
    return {
        "status": "pending",
        "message": "Once an admin approves the request, you will receive an email with login details.",
    }


@router.post("/approve")
def approve_email(email: EmailStr) -> dict[str, Any]:
    """Temporary admin helper. Protect this behind your own admin auth before production."""
    store = _load_store()
    email = email.lower()
    approved = set(store.get("approved", []))
    approved.add(email)
    store["approved"] = sorted(approved)
    store["pending"] = [item for item in store.get("pending", []) if item.get("email") != email]
    _save_store(store)
    return {"ok": True, "approved": email}


@router.get("/session")
def session(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return {"user": user}


@router.post("/logout")
def logout() -> dict[str, bool]:
    return {"ok": True}


def add_cors(app) -> None:
    origins = [
        item.strip()
        for item in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if item.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

"""Signup, email verification, login/logout, and password reset."""

import logging
from typing import Annotated, Union

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from tessara_server.configuration.settings import application_settings
from tessara_server.data.database.dependencies import DatabaseSessionDependency
from tessara_server.data.repository import user_repository
from tessara_server.utility.email import send_email
from tessara_server.web.csrf import verify_csrf
from tessara_server.web.dependencies.auth import _SESSION_COOKIE, make_session_cookie
from tessara_server.web.dependencies.tokens import (
    decode_email_token,
    decode_reset_token,
    make_email_token,
    make_reset_token,
    nonce_matches,
)
from tessara_server.web.rate_limit import limiter
from tessara_server.web.templates import templates

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

_CTX = {"settings": application_settings}


def _safe_next(next_path: str | None) -> str:
    if next_path and next_path.startswith("/") and not next_path.startswith("//"):
        return next_path
    return "/generate"


@router.get("/signup", response_class=HTMLResponse)
async def get_signup(request: Request, error: str | None = None) -> HTMLResponse:
    return templates.TemplateResponse(request, "signup.html", {**_CTX, "error": error})


@router.post("/signup", response_model=None)
@limiter.limit(application_settings.rate_limit_signup)
async def post_signup(
    request: Request,
    session: DatabaseSessionDependency,
    _csrf: Annotated[None, Depends(verify_csrf)],
    email: str = Form(...),
    password: str = Form(...),
) -> Union[HTMLResponse, RedirectResponse]:
    if len(password) < 8:
        return templates.TemplateResponse(
            request,
            "signup.html",
            {**_CTX, "error": "Password must be at least 8 characters."},
            status_code=400,
        )

    existing = await user_repository.get_by_email(session, email)
    if existing:
        return templates.TemplateResponse(
            request,
            "signup.html",
            {**_CTX, "error": "An account with that email already exists."},
            status_code=400,
        )

    user = await user_repository.create(session, email, password)
    verify_url = f"{application_settings.public_base_url}/verify-email?token={make_email_token(user)}"
    await send_email(
        user.email,
        f"Verify your {application_settings.project_name} account",
        f"Confirm your email address:\n\n{verify_url}\n",
    )
    return templates.TemplateResponse(request, "verify_notice.html", {**_CTX, "email": user.email})


@router.get("/verify-email", response_class=HTMLResponse)
async def verify_email(
    request: Request,
    session: DatabaseSessionDependency,
    token: str,
) -> HTMLResponse:
    data = decode_email_token(token)
    if not data:
        return templates.TemplateResponse(
            request,
            "error.html",
            {**_CTX, "error": "That verification link is invalid or has expired."},
            status_code=400,
        )
    user = await user_repository.get_by_id(session, data["uid"])
    if not user or not nonce_matches(user, data["nonce"]):
        return templates.TemplateResponse(
            request,
            "error.html",
            {**_CTX, "error": "That verification link is invalid or has expired."},
            status_code=400,
        )
    await user_repository.set_verified(session, user.id)
    return templates.TemplateResponse(
        request, "login.html", {**_CTX, "error": None, "next": None, "flash": "Email verified — sign in below."}
    )


@router.get("/login", response_class=HTMLResponse)
async def get_login(
    request: Request, error: str | None = None, next: str | None = None
) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "login.html", {**_CTX, "error": error, "next": next, "flash": None}
    )


@router.post("/login", response_model=None)
@limiter.limit(application_settings.rate_limit_login)
async def post_login(
    request: Request,
    session: DatabaseSessionDependency,
    _csrf: Annotated[None, Depends(verify_csrf)],
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form(""),
) -> Union[HTMLResponse, RedirectResponse]:
    user = await user_repository.verify_password(session, email, password)
    if not user:
        return templates.TemplateResponse(
            request,
            "login.html",
            {**_CTX, "error": "Invalid email or password", "next": next, "flash": None},
            status_code=401,
        )
    if not user.is_verified:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                **_CTX,
                "error": "Please verify your email before signing in — check your inbox for the link.",
                "next": next,
                "flash": None,
            },
            status_code=401,
        )

    token = make_session_cookie(user)
    response = RedirectResponse(_safe_next(next), status_code=303)
    response.set_cookie(
        _SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=application_settings.session_max_age,
    )
    return response


@router.post("/logout")
async def post_logout(_csrf: Annotated[None, Depends(verify_csrf)]) -> RedirectResponse:
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(_SESSION_COOKIE)
    return response


@router.get("/forgot-password", response_class=HTMLResponse)
async def get_forgot_password(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "forgot_password.html", {**_CTX, "sent": False})


@router.post("/forgot-password", response_model=None)
@limiter.limit(application_settings.rate_limit_forgot_password)
async def post_forgot_password(
    request: Request,
    session: DatabaseSessionDependency,
    _csrf: Annotated[None, Depends(verify_csrf)],
    email: str = Form(...),
) -> HTMLResponse:
    user = await user_repository.get_by_email(session, email)
    if user and user.is_active:
        reset_url = f"{application_settings.public_base_url}/reset-password?token={make_reset_token(user)}"
        await send_email(
            user.email,
            f"Reset your {application_settings.project_name} password",
            f"Reset your password:\n\n{reset_url}\n\nIf you didn't request this, ignore this email.\n",
        )
    # Always show the same response, whether or not the email exists — avoids
    # leaking which addresses have accounts.
    return templates.TemplateResponse(request, "forgot_password.html", {**_CTX, "sent": True})


@router.get("/reset-password", response_class=HTMLResponse)
async def get_reset_password(request: Request, token: str) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "reset_password.html", {**_CTX, "token": token, "error": None}
    )


@router.post("/reset-password", response_model=None)
async def post_reset_password(
    request: Request,
    session: DatabaseSessionDependency,
    _csrf: Annotated[None, Depends(verify_csrf)],
    token: str = Form(...),
    password: str = Form(...),
) -> Union[HTMLResponse, RedirectResponse]:
    data = decode_reset_token(token)
    if not data:
        return templates.TemplateResponse(
            request,
            "error.html",
            {**_CTX, "error": "That password reset link is invalid or has expired."},
            status_code=400,
        )
    user = await user_repository.get_by_id(session, data["uid"])
    if not user or not nonce_matches(user, data["nonce"]):
        return templates.TemplateResponse(
            request,
            "error.html",
            {**_CTX, "error": "That password reset link is invalid or has expired."},
            status_code=400,
        )
    if len(password) < 8:
        return templates.TemplateResponse(
            request,
            "reset_password.html",
            {**_CTX, "token": token, "error": "Password must be at least 8 characters."},
            status_code=400,
        )
    await user_repository.set_password(session, user.id, password)
    return templates.TemplateResponse(
        request, "login.html", {**_CTX, "error": None, "next": None, "flash": "Password updated — sign in below."}
    )

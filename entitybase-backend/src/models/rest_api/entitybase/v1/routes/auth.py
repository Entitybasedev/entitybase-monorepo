"""Authentication routes: register and login."""

import logging

from fastapi import APIRouter, HTTPException, Request

from models.config.settings import settings
from models.data.rest_api.v1.entitybase.request.auth import (
    LoginRequest,
    RegisterRequest,
)
from models.data.rest_api.v1.entitybase.response.auth import AuthResponse
from models.rest_api.entitybase.v1.services.auth_service import (
    create_token,
    hash_password,
    verify_password,
)
from models.rest_api.utils import raise_validation_error, validate_state_clients

logger = logging.getLogger(__name__)

auth_router = APIRouter(tags=["auth"])


@auth_router.post("/auth/register", response_model=AuthResponse)
def register(request: RegisterRequest, req: Request) -> AuthResponse:
    """Register a new user with username and password.

    Returns a session token on success. When user_id is omitted the next
    free numeric user ID is assigned.
    """
    state = req.app.state.state_handler
    validate_state_clients(state)
    repo = state.db_client.user_repository

    existing = repo.get_credentials_by_username(request.username)
    if existing is not None:
        raise_validation_error("Username already taken", status_code=400)

    user_id = request.user_id
    if user_id <= 0:
        # Auto-assign: retry on collisions (concurrent registrations can
        # compute the same next id)
        for _ in range(5):
            candidate = repo.get_next_user_id()
            if repo.user_exists(candidate):
                continue
            created = repo.create_user(candidate)
            if not getattr(created, "success", False):
                continue
            user_id = candidate
            break
        else:
            raise_validation_error(
                "Could not assign a user ID, try again", status_code=503
            )
    else:
        if repo.user_exists(user_id):
            raise_validation_error(
                f"User {user_id} already exists", status_code=400
            )
        created = repo.create_user(user_id)
        if not getattr(created, "success", False):
            raise_validation_error("Failed to create user", status_code=500)

    credentials = repo.create_credentials(
        user_id, request.username, hash_password(request.password)
    )
    if not getattr(credentials, "success", False):
        raise_validation_error("Failed to store credentials", status_code=500)

    token = _issue_token(user_id, request.username)
    return AuthResponse(token=token, user_id=user_id, username=request.username)


@auth_router.post("/auth/login", response_model=AuthResponse)
def login(request: LoginRequest, req: Request) -> AuthResponse:
    """Log in with username and password.

    Returns a session token for the user.
    """
    state = req.app.state.state_handler
    validate_state_clients(state)
    repo = state.db_client.user_repository

    credentials = repo.get_credentials_by_username(request.username)
    if credentials is None or not verify_password(
        request.password, credentials.password_hash
    ):
        logger.info(f"Failed login attempt for {request.username}")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user_id = credentials.user_id
    token = _issue_token(user_id, request.username)
    return AuthResponse(token=token, user_id=user_id, username=request.username)


def _issue_token(user_id: int, username: str) -> str:
    """Create a signed token for the user."""
    try:
        token: str = create_token(
            user_id,
            username,
            settings.auth_signing_secret,
            settings.auth_token_expiry_hours,
        )
        return token
    except ValueError as e:
        logger.error(f"Token creation failed: {e}")
        # follow_imports=skip hides raise_validation_error's NoReturn type
        # from mypy, so raise directly here
        raise HTTPException(status_code=500, detail="Failed to create token") from e

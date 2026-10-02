"""Main REST API application module."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from jsonschema import ValidationError  # type: ignore[import-untyped]
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
# from starlette.exceptions import StarletteHTTPException

from models.config.settings import settings
from models.config.version import API_VERSION
from models.rest_api.entitybase.v1.endpoints import v1_router
from models.rest_api.entitybase.v1.handlers.state import StateHandler
from models.rest_api.entitybase.v1.routes import include_routes
from models.rest_api.entitybase.v1.services.auth_service import decode_token, hash_password
from models.rest_api.utils import raise_validation_error

aws_loggers = [
    "botocore",
    "boto3",
    "urllib3",
    "s3transfer",
    "botocore.hooks",
    "botocore.retryhandler",
    "botocore.utils",
    "botocore.parsers",
    "botocore.endpoint",
    "botocore.auth",
]

aiokafka_loggers = [
    "aiokafka.conn",
    "aiokafka.consumer.group_coordinator",
    "aiokafka.consumer.fetcher",
    "aiokafka.consumer.subscription_state",
    "aiokafka.coordinator.assignor",
    "aiokafka.coordinator.heartbeat",
]

for logger_name in aws_loggers:
    logging.getLogger(logger_name).setLevel(logging.INFO)

for logger_name in aiokafka_loggers:
    logging.getLogger(logger_name).setLevel(logging.INFO)

logging.basicConfig(level=settings.get_log_level())

logger = logging.getLogger(__name__)


class StartupMiddleware(BaseHTTPMiddleware):
    """Middleware to protect endpoints during application startup.

    Returns 503 for non-essential endpoints while state_handler is initializing.
    Always allows /health, /docs, and /openapi.json through.
    """

    async def dispatch(
        self, request: StarletteRequest, call_next: Any
    ) -> StarletteResponse:
        allowed_paths = {"/health", "/docs", "/openapi.json", "/redoc", "/version"}
        request_path = request.url.path

        if request_path not in allowed_paths:
            state_handler = getattr(request.app.state, "state_handler", None)
            if state_handler is None:
                logger.debug(
                    f"Rejecting request to {request_path} during initialization"
                )
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "Service Unavailable",
                        "message": "Application is initializing. Please try again shortly.",
                    },
                )

        return await call_next(request)


WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware resolving the acting user from a bearer token.

    A valid Authorization: Bearer token is the source of truth for the
    user: its user_id is injected as the X-User-ID header for downstream
    routes, which no longer need the client to send it. Clients may still
    send X-User-ID explicitly; a mismatch with the token is rejected with
    403. A present but invalid token is rejected with 401 on any request.

    Auth is enforced (writes without a token get 401) only when
    settings.auth_secret is configured; otherwise the legacy header-based
    behavior is preserved and reads/writes pass through unchanged.
    Exempt paths (always public): /health, /docs, /openapi.json, /redoc,
    /version, {api_prefix}/auth/login and {api_prefix}/auth/register.
    """

    async def dispatch(
        self, request: StarletteRequest, call_next: Any
    ) -> StarletteResponse:
        authorization = request.headers.get("Authorization", "")
        payload = None
        if authorization.startswith("Bearer "):
            token = authorization.removeprefix("Bearer ").strip()
            try:
                payload = decode_token(token, settings.auth_signing_secret)
            except ValueError as e:
                logger.info(f"Rejected token: {e}")
                return _auth_error(401, str(e))

            user_id_header = request.headers.get("X-User-ID")
            if user_id_header is None:
                request.scope["headers"].append(
                    (b"x-user-id", str(payload.user_id).encode())
                )
            elif str(payload.user_id) != user_id_header:
                return _auth_error(403, "X-User-ID does not match token")

        if settings.auth_secret and request.method in WRITE_METHODS:
            exempt = {
                "/health",
                "/docs",
                "/openapi.json",
                "/redoc",
                "/version",
                f"{settings.api_prefix}/auth/login",
                f"{settings.api_prefix}/auth/register",
            }
            if payload is None and request.url.path not in exempt:
                return _auth_error(401, "Missing bearer token")

        return await call_next(request)


def _auth_error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": "auth_error", "message": message},
    )


@asynccontextmanager
async def lifespan(app_: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown tasks."""
    try:
        state_handler = await _initialize_state_handler()
        state_handler.health_check()
        await _ensure_stream_producer(state_handler)
        await _create_database_tables(state_handler)
        _ensure_import_user(state_handler)
        _ensure_demo_user(state_handler)
        await _initialize_app_state(app_, state_handler)
        yield
    except Exception as e:
        logger.error(
            f"Failed to initialize clients: {type(e).__name__}: {e}", exc_info=True
        )
        raise
    finally:
        await _cleanup_app_state(app_)


async def _initialize_state_handler() -> StateHandler:
    """Initialize the state handler."""
    state_handler = StateHandler(settings=settings)
    state_handler.start()
    return state_handler


async def _ensure_stream_producer(state_handler: StateHandler) -> None:
    """Start the stream producer so the configured topics exist."""
    if not state_handler.settings.streaming_enabled:
        logger.debug("Streaming disabled, skipping stream producer startup")
        return
    producer = state_handler.entity_change_stream_producer
    if producer is None:
        logger.warning("Stream producer not configured, skipping topic creation")
        return
    try:
        await producer.start()
        logger.info("Stream producer started; topics ensured")
    except Exception as e:
        logger.warning(
            f"Could not start stream producer at startup: {type(e).__name__}: {e}"
        )


async def _create_database_tables(state_handler: StateHandler) -> None:
    """Create database tables on startup."""
    try:
        logger.debug("Creating database tables...")
        state_handler.db_client.create_tables()
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.warning(f"Could not create database tables on startup: {e}")
        logger.info("Tables will be created when first accessed or in tests")


def _ensure_import_user(state_handler: StateHandler) -> None:
    """Ensure the reserved import system user exists (idempotent).

    The import user (user_id 0, username from settings.import_username)
    owns bulk-imported entities and cannot log in (no password hash).
    """
    import_user_id = 0
    try:
        repo = state_handler.db_client.user_repository
        if not repo.user_exists(import_user_id):
            created = repo.create_user(import_user_id)
            if not getattr(created, "success", False):
                logger.warning(f"Could not create import user: {created.error}")
                return
        if repo.get_credentials_by_username(settings.import_username) is None:
            credentials = repo.create_credentials(
                import_user_id, settings.import_username, ""
            )
            if not getattr(credentials, "success", False):
                logger.warning(
                    f"Could not label import user: {credentials.error}"
                )
                return
        logger.info(f"Import user ready: {settings.import_username}")
    except Exception as e:
        logger.warning(f"Could not ensure import user: {e}")


def _ensure_demo_user(state_handler: StateHandler) -> None:
    """Ensure the demo user exists (idempotent).

    The demo user is a regular account for local testing; it can log in
    with credentials from settings (DEMO_USERNAME / DEMO_PASSWORD,
    default demo/demo).
    """
    try:
        repo = state_handler.db_client.user_repository
        if repo.get_credentials_by_username(settings.demo_username) is not None:
            logger.debug(f"Demo user exists: {settings.demo_username}")
            return
        next_id = repo.get_next_user_id()
        created = repo.create_user(next_id)
        if not getattr(created, "success", False):
            logger.warning(f"Could not create demo user: {created.error}")
            return
        credentials = repo.create_credentials(
            next_id,
            settings.demo_username,
            hash_password(settings.demo_password),
        )
        if not getattr(credentials, "success", False):
            logger.warning(f"Could not store demo credentials: {credentials.error}")
            return
        logger.info(f"Demo user ready: {settings.demo_username} (user {next_id})")
    except Exception as e:
        logger.warning(f"Could not ensure demo user: {e}")


async def _initialize_app_state(app_: FastAPI, state_handler: StateHandler) -> None:
    """Initialize app state and log success."""
    logger.info("Clients, validator, and enumeration service initialized successfully")
    app_.state.state_handler = state_handler


async def _cleanup_app_state(app_: FastAPI) -> None:
    """Cleanup app state on shutdown."""
    if hasattr(app_.state, "state_handler") and app_.state.state_handler:
        await app_.state.state_handler.async_shutdown()
        app_.state.state_handler.disconnect()
        logger.info("All clients disconnected")


app_kwargs: dict = {
    "title": "Entitybase-backend",
    "version": API_VERSION,
    "openapi_version": "3.1",
    "lifespan": lifespan,
    "response_model_by_alias": True,
}
if settings.api_description:
    app_kwargs["description"] = settings.api_description

app = FastAPI(**app_kwargs)
app.add_middleware(AuthMiddleware)
app.add_middleware(StartupMiddleware)


@app.exception_handler(ValidationError)
async def validation_error_handler(exc: ValidationError) -> JSONResponse:
    """Handle JSON schema validation errors and return formatted response."""
    error_field = f"{'/' + '/'.join(str(p) for p in exc.path) if exc.path else '/'}"
    error_message = exc.message
    return JSONResponse(
        status_code=400,
        content={
            "error": "validation_error",
            "message": "JSON schema validation failed",
            "details": [
                {
                    "field": error_field,
                    "message": error_message,
                    "path": list(exc.path),
                }
            ],
        },
    )


@app.exception_handler(HTTPException)
async def starlette_http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Handle StarletteHTTPException with proper JSON formatting."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail if exc.detail else "Not Found",
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all exceptions and return formatted JSON response."""
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}", exc_info=True)

    content = {
        "error": "internal_error",
        "message": str(exc),
        "detail": f"{type(exc).__name__}: {exc}",
    }

    return JSONResponse(
        status_code=500,
        content=content,
    )


include_routes(app)

app.include_router(v1_router, prefix=settings.api_prefix)
# app.include_router(wikibase_v1_router, prefix="/wikibase/v1")


@app.get("/v1/openapi.json")
async def get_openapi() -> dict:
    """Retrieve the OpenAPI document."""
    openapi = app.openapi()
    if not isinstance(openapi, dict):
        # follow_imports=skip hides raise_validation_error's NoReturn type
        # from mypy, so raise directly here
        raise HTTPException(
            status_code=500, detail="OpenAPI schema generation failed"
        )
    return openapi


@app.get("/")
async def redirect_to_docs() -> RedirectResponse:
    """Redirect to the OpenAPI docs."""
    return RedirectResponse(url="/docs")

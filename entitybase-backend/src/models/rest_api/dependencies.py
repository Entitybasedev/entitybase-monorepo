"""Route dependencies for identifying the acting user.

AuthMiddleware publishes the user id decoded from a bearer token as
``scope["auth_user_id"]``. These dependencies read it so a route never has to
trust a user id that came from the client (a path or query parameter).

They deliberately do not consult ``settings.auth_secret``: whether anonymous
writes are allowed in general is a deployment choice, but a route that acts on
one specific user's data always requires that user's token.
"""

from fastapi import HTTPException, Request

AUTH_USER_ID_SCOPE_KEY = "auth_user_id"


def current_user_id(req: Request) -> int:
    """Return the id of the authenticated caller.

    Raises 401 when the request carries no valid bearer token, so a client can
    never read or write another user's data by guessing an id.
    """
    user_id = req.scope.get(AUTH_USER_ID_SCOPE_KEY)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return int(user_id)


def require_self(user_id: int, req: Request) -> int:
    """Return ``user_id`` after checking the caller owns it.

    Use as a FastAPI dependency on routes that take a user id in the path:
    ``_: int = Depends(require_self)``. Raises 401 without a token and 403 when
    the token belongs to somebody else.
    """
    caller_id = current_user_id(req)
    if caller_id != user_id:
        raise HTTPException(
            status_code=403,
            detail=f"User {user_id} does not match the authenticated user",
        )
    return caller_id

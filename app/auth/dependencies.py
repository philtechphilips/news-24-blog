import uuid
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.database import DbSession
from app.core.security import decode_access_token
from app.users import service as users_service
from app.users.models import Role, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
# Same, but a missing token isn't an error (for routes guests can use too).
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: DbSession
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = uuid.UUID(decode_access_token(token)["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise credentials_exception from None

    user = users_service.get_user(db, user_id)
    if user is None:
        raise credentials_exception
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_optional_user(
    token: Annotated[str | None, Depends(optional_oauth2_scheme)], db: DbSession
) -> User | None:
    """The logged-in user, or None for guests. A bad or expired token counts
    as a guest rather than an error."""
    if token is None:
        return None
    try:
        return get_current_user(token, db)
    except HTTPException:
        return None


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_roles(*roles: Role) -> Callable[[User], User]:
    """Dependency that allows only users with one of the given roles.

    Use it in a route signature or a router's dependencies:

        @router.get("/reports", dependencies=[Depends(require_roles(Role.ADMIN))])
    """

    def check_role(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to perform this action",
            )
        return current_user

    return check_role


AdminUser = Annotated[User, Depends(require_roles(Role.ADMIN))]

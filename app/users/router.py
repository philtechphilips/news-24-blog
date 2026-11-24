import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.auth.dependencies import AdminUser, CurrentUser
from app.core.database import DbSession
from app.users import service
from app.users.models import Role, User
from app.users.schemas import ProfileUpdate, RoleUpdate, UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])

Limit = Annotated[int, Query(ge=1, le=100)]
Skip = Annotated[int, Query(ge=0)]


def _get_or_404(db: DbSession, user_id: uuid.UUID) -> User:
    user = service.get_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )
    return user


def _ensure_email_free(db: DbSession, email: str) -> None:
    if service.get_user_by_email(db, email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {email} already exists",
        )


def _not_yourself(user_id: uuid.UUID, admin: User, message: str) -> None:
    # Stops the last admin from locking everyone out (demoting or deleting
    # themselves).
    if user_id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def create_user(user_in: UserCreate, db: DbSession):
    _ensure_email_free(db, user_in.email)
    # Sign-ups are always regular users; admins are made by another admin
    # (see the admin endpoints below) or with `uv run poe createadmin`.
    return service.create_user(db, user_in)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: CurrentUser):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(body: ProfileUpdate, db: DbSession, current_user: CurrentUser):
    """Change your display name (shown on your comments)."""
    return service.update_profile(db, current_user, body)


@router.get("/", response_model=list[UserResponse])
def list_users(db: DbSession, _: AdminUser, limit: Limit = 10, skip: Skip = 0):
    return service.list_users(db, limit, skip)


# ---------- Admin management (admins only) ----------
# Declared before /{user_id} so "admins" isn't parsed as a user id.


@router.get("/admins", response_model=list[UserResponse], tags=["Admins"])
def list_admins(db: DbSession, _: AdminUser, limit: Limit = 100, skip: Skip = 0):
    return service.list_users(db, limit, skip, role=Role.ADMIN)


@router.post(
    "/admins",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    tags=["Admins"],
)
def create_admin(user_in: UserCreate, db: DbSession, _: AdminUser):
    """Create a new account that is an admin from the start."""
    _ensure_email_free(db, user_in.email)
    return service.create_user(db, user_in, role=Role.ADMIN)


@router.put("/{user_id}/admin", response_model=UserResponse, tags=["Admins"])
def make_admin(user_id: uuid.UUID, db: DbSession, admin: AdminUser):
    """Give an existing user admin rights. Safe to call twice."""
    _not_yourself(user_id, admin, "You're already an admin")
    return service.set_role(db, _get_or_404(db, user_id), Role.ADMIN)


@router.delete("/{user_id}/admin", response_model=UserResponse, tags=["Admins"])
def remove_admin(user_id: uuid.UUID, db: DbSession, admin: AdminUser):
    """Take admin rights away; the account stays as a regular user."""
    _not_yourself(user_id, admin, "You can't remove your own admin rights")
    return service.set_role(db, _get_or_404(db, user_id), Role.USER)


# ---------- Single user ----------


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: uuid.UUID, db: DbSession, current_user: CurrentUser):
    if current_user.id != user_id and current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to perform this action",
        )
    return _get_or_404(db, user_id)


@router.patch("/{user_id}/role", response_model=UserResponse)
def update_role(user_id: uuid.UUID, body: RoleUpdate, db: DbSession, admin: AdminUser):
    _not_yourself(user_id, admin, "You can't change your own role")
    return service.set_role(db, _get_or_404(db, user_id), body.role)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: uuid.UUID, db: DbSession, admin: AdminUser):
    """Permanently delete an account. Admins only."""
    _not_yourself(user_id, admin, "You can't delete your own account here")
    service.delete_user(db, _get_or_404(db, user_id))

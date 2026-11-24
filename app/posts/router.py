from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.auth.dependencies import AdminUser, CurrentUser
from app.core.database import DbSession
from app.posts import service
from app.users.models import Role
from app.users.schemas import RoleUpdate, UserCreate, UserResponse

router = APIRouter(prefix="/posts", tags=["Posts"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def create_post(user_in: UserCreate, db: DbSession):
    return service.create_post(db, user_in)


@router.get("/", response_model=UserResponse)
def get_posts(current_user: CurrentUser):
    posts = service.get_posts(db, user_id)
    return posts


@router.get("/{post_id}", response_model=UserResponse)
def get_post(user_id: int, db: DbSession, current_user: CurrentUser):
    post = service.get_post(db, user_id)
    return post


@router.patch("/{user_id}", response_model=UserResponse)
def update_post(user_id: int, body: RoleUpdate, db: DbSession, admin: AdminUser):
    return service.update_post(db, user, body.role)

@router.delete("/{user_id}", response_model=UserResponse)
def update_post(user_id: int, body: RoleUpdate, db: DbSession, admin: AdminUser):
    return service.delete_post(db, user, body.role)

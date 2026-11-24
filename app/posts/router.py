from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.auth.dependencies import AdminUser
from app.core.database import DbSession
from app.posts import service
from app.posts.models import Posts
from app.posts.schemas import PostCreate, PostResponse, PostUpdate

router = APIRouter(prefix="/posts", tags=["Posts"])

Limit = Annotated[int, Query(ge=1, le=100)]
Skip = Annotated[int, Query(ge=0)]


def _get_or_404(db: DbSession, post_id: UUID) -> Posts:
    post = service.get_post(db, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id {post_id} not found",
        )
    return post


def _bad_request(error: Exception) -> HTTPException:
    code = (
        status.HTTP_409_CONFLICT
        if isinstance(error, service.SlugTakenError)
        else status.HTTP_422_UNPROCESSABLE_CONTENT
    )
    return HTTPException(status_code=code, detail=str(error))


@router.get("/", response_model=list[PostResponse])
def list_posts(
    db: DbSession, category_id: UUID | None = None, limit: Limit = 20, skip: Skip = 0
):
    return service.list_published(db, category_id, limit, skip)


# Declared before /{post_id} so "all" isn't parsed as an id.
@router.get("/all", response_model=list[PostResponse])
def list_all_posts(db: DbSession, _: AdminUser, limit: Limit = 100, skip: Skip = 0):
    return service.list_all(db, limit, skip)


@router.get("/slug/{slug}", response_model=PostResponse)
def get_post_by_slug(slug: str, db: DbSession):
    post = service.get_published_by_slug(db, slug)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Post {slug!r} not found"
        )
    return post


@router.get("/{post_id}", response_model=PostResponse)
def get_post(post_id: UUID, db: DbSession, _: AdminUser):
    return _get_or_404(db, post_id)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=PostResponse)
def create_post(body: PostCreate, db: DbSession, _: AdminUser):
    try:
        return service.create_post(db, body)
    except (service.SlugTakenError, service.UnknownCategoryError) as error:
        raise _bad_request(error) from None


@router.patch("/{post_id}", response_model=PostResponse)
def update_post(post_id: UUID, body: PostUpdate, db: DbSession, _: AdminUser):
    post = _get_or_404(db, post_id)
    try:
        return service.update_post(db, post, body)
    except (service.SlugTakenError, service.UnknownCategoryError) as error:
        raise _bad_request(error) from None


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: UUID, db: DbSession, _: AdminUser):
    service.delete_post(db, _get_or_404(db, post_id))

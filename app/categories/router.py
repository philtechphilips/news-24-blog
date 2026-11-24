from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.auth.dependencies import AdminUser
from app.categories import service
from app.categories.models import Categories
from app.categories.schemas import CategoryCreate, CategoryResponse, CategoryUpdate
from app.core.database import DbSession

router = APIRouter(prefix="/categories", tags=["Categories"])


def _get_or_404(db: DbSession, category_id: UUID) -> Categories:
    category = service.get_category(db, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id {category_id} not found",
        )
    return category


def _ensure_name_free(db: DbSession, name: str) -> None:
    if service.get_category_by_name(db, name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category {name!r} already exists",
        )


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=CategoryResponse)
def create_category(body: CategoryCreate, db: DbSession, _: AdminUser):
    _ensure_name_free(db, body.name)
    return service.create_category(db, body)


@router.get("/", response_model=list[CategoryResponse])
def list_categories(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    skip: Annotated[int, Query(ge=0)] = 0,
):
    return service.list_categories(db, limit, skip)


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: UUID, db: DbSession):
    return _get_or_404(db, category_id)


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: UUID, body: CategoryUpdate, db: DbSession, _: AdminUser
):
    category = _get_or_404(db, category_id)
    if body.name is not None and body.name != category.name:
        _ensure_name_free(db, body.name)
    return service.update_category(db, category, body)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: UUID, db: DbSession, _: AdminUser):
    service.delete_category(db, _get_or_404(db, category_id))

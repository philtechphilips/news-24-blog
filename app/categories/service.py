from uuid import UUID

from sqlalchemy.orm import Session

from app.categories.models import Categories
from app.categories.schemas import CategoryCreate, CategoryUpdate
from app.core import crud


def get_category(db: Session, category_id: UUID) -> Categories | None:
    return crud.fetch_one(db, Categories, {"id": category_id})


def get_category_by_name(db: Session, name: str) -> Categories | None:
    return crud.fetch_one(db, Categories, {"name": name})


def list_categories(db: Session, limit: int = 50, skip: int = 0) -> list[Categories]:
    return crud.fetch(
        db, Categories, sort_by="name", sort_type="asc", limit=limit, skip=skip
    )


def create_category(db: Session, category_in: CategoryCreate) -> Categories:
    return crud.create(db, Categories, category_in.model_dump())


def update_category(
    db: Session, category: Categories, category_in: CategoryUpdate
) -> Categories:
    data = category_in.model_dump(exclude_unset=True)
    return crud.update(db, Categories, {"id": category.id}, data)


def delete_category(db: Session, category: Categories) -> None:
    crud.hard_delete(db, Categories, {"id": category.id})

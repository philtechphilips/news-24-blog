from uuid import UUID

from sqlalchemy.orm import Session

from app.core import crud
from app.core.slugs import check_slug_for_update, slug_for_create
from app.writers.models import Writers
from app.writers.schemas import WriterCreate, WriterUpdate


def list_writers(db: Session, limit: int = 100, skip: int = 0) -> list[Writers]:
    # Oldest first, so the longest-serving writers lead the list.
    return crud.fetch(db, Writers, sort_type="asc", limit=limit, skip=skip)


def get_writer(db: Session, writer_id: UUID) -> Writers | None:
    return crud.fetch_one(db, Writers, {"id": writer_id})


def get_writer_by_slug(db: Session, slug: str) -> Writers | None:
    return crud.fetch_one(db, Writers, {"slug": slug})


def create_writer(db: Session, writer_in: WriterCreate) -> Writers:
    data = writer_in.model_dump()
    data["slug"] = slug_for_create(db, Writers, "writer", data["slug"], data["name"])
    return crud.create(db, Writers, data)


def update_writer(db: Session, writer: Writers, writer_in: WriterUpdate) -> Writers:
    data = writer_in.model_dump(exclude_unset=True)
    if data.get("slug"):
        data["slug"] = check_slug_for_update(
            db, Writers, "writer", data["slug"], writer.id
        )
    required = {"name", "role", "slug", "bio", "beats", "social"}
    return crud.patch(db, writer, data, required)


def delete_writer(db: Session, writer: Writers) -> None:
    # Their posts and podcasts stay, without a byline (ON DELETE SET NULL).
    crud.hard_delete(db, Writers, {"id": writer.id})

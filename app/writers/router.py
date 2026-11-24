from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.auth.dependencies import AdminUser
from app.core.database import DbSession
from app.core.slugs import SlugTakenError, to_http_error
from app.writers import service
from app.writers.models import Writers
from app.writers.schemas import WriterCreate, WriterResponse, WriterUpdate

router = APIRouter(prefix="/writers", tags=["Writers"])


def _get_or_404(db: DbSession, writer_id: UUID) -> Writers:
    writer = service.get_writer(db, writer_id)
    if writer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Writer with id {writer_id} not found",
        )
    return writer


@router.get("/", response_model=list[WriterResponse])
def list_writers(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    skip: Annotated[int, Query(ge=0)] = 0,
):
    """Anyone can read writer profiles."""
    return service.list_writers(db, limit, skip)


# Declared before /{writer_id} so "slug" isn't parsed as an id.
@router.get("/slug/{slug}", response_model=WriterResponse)
def get_writer_by_slug(slug: str, db: DbSession):
    writer = service.get_writer_by_slug(db, slug)
    if writer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Writer {slug!r} not found"
        )
    return writer


@router.get("/{writer_id}", response_model=WriterResponse)
def get_writer(writer_id: UUID, db: DbSession):
    return _get_or_404(db, writer_id)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=WriterResponse)
def create_writer(body: WriterCreate, db: DbSession, _: AdminUser):
    try:
        return service.create_writer(db, body)
    except SlugTakenError as error:
        raise to_http_error(error) from None


@router.patch("/{writer_id}", response_model=WriterResponse)
def update_writer(writer_id: UUID, body: WriterUpdate, db: DbSession, _: AdminUser):
    writer = _get_or_404(db, writer_id)
    try:
        return service.update_writer(db, writer, body)
    except SlugTakenError as error:
        raise to_http_error(error) from None


@router.delete("/{writer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_writer(writer_id: UUID, db: DbSession, _: AdminUser):
    service.delete_writer(db, _get_or_404(db, writer_id))

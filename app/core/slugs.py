"""URL slugs shared by features that have them (posts, podcasts, writers)."""

import re
import unicodedata
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session


class SlugTakenError(Exception):
    def __init__(self, kind: str, slug: str):
        super().__init__(f"A {kind} with slug {slug!r} already exists")


class UnknownReferenceError(Exception):
    """A request pointed at a related row (category, writer...) that doesn't exist."""

    def __init__(self, kind: str, ref_id: UUID):
        super().__init__(f"{kind.capitalize()} with id {ref_id} not found")


def to_http_error(error: SlugTakenError | UnknownReferenceError) -> HTTPException:
    code = (
        status.HTTP_409_CONFLICT
        if isinstance(error, SlugTakenError)
        else status.HTTP_422_UNPROCESSABLE_CONTENT
    )
    return HTTPException(status_code=code, detail=str(error))


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:270].strip("-") or "post"


def slug_taken(
    db: Session, model: type[Any], slug: str, exclude_id: UUID | None = None
) -> bool:
    row = db.query(model).filter_by(slug=slug).first()
    return row is not None and row.id != exclude_id


def unique_slug(db: Session, model: type[Any], base: str) -> str:
    slug, n = base, 2
    while slug_taken(db, model, slug):
        slug, n = f"{base}-{n}", n + 1
    return slug


def slug_for_create(
    db: Session, model: type[Any], kind: str, requested: str | None, fallback: str
) -> str:
    """An explicit slug must be free; otherwise one is made unique from `fallback`."""
    if requested:
        slug = slugify(requested)
        if slug_taken(db, model, slug):
            raise SlugTakenError(kind, slug)
        return slug
    return unique_slug(db, model, slugify(fallback))


def check_slug_for_update(
    db: Session, model: type[Any], kind: str, slug: str, row_id: UUID
) -> str:
    slug = slugify(slug)
    if slug_taken(db, model, slug, exclude_id=row_id):
        raise SlugTakenError(kind, slug)
    return slug

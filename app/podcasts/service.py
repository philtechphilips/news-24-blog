from uuid import UUID

from sqlalchemy.orm import Session

from app.core import crud
from app.core.slugs import UnknownReferenceError, check_slug_for_update, slug_for_create
from app.podcasts.models import Podcasts
from app.podcasts.schemas import PodcastCreate, PodcastUpdate
from app.writers.models import Writers


def _check_host(db: Session, host_id: UUID | None) -> None:
    if host_id and crud.fetch_one(db, Writers, {"id": host_id}) is None:
        raise UnknownReferenceError("writer", host_id)


def list_published(db: Session, limit: int = 20, skip: int = 0) -> list[Podcasts]:
    return crud.fetch(db, Podcasts, {"is_published": True}, limit=limit, skip=skip)


def list_all(db: Session, limit: int = 100, skip: int = 0) -> list[Podcasts]:
    return crud.fetch(db, Podcasts, sort_by="updated_at", limit=limit, skip=skip)


def get_podcast(db: Session, podcast_id: UUID) -> Podcasts | None:
    return crud.fetch_one(db, Podcasts, {"id": podcast_id})


def get_published_by_slug(db: Session, slug: str) -> Podcasts | None:
    return crud.fetch_one(db, Podcasts, {"slug": slug, "is_published": True})


def create_podcast(db: Session, podcast_in: PodcastCreate) -> Podcasts:
    data = podcast_in.model_dump()
    _check_host(db, data["host_id"])
    data["slug"] = slug_for_create(db, Podcasts, "podcast", data["slug"], data["title"])
    return crud.create(db, Podcasts, data)


def update_podcast(
    db: Session, podcast: Podcasts, podcast_in: PodcastUpdate
) -> Podcasts:
    # Only the fields the client sent, so optional ones can be cleared with null.
    data = podcast_in.model_dump(exclude_unset=True)
    if "host_id" in data:
        _check_host(db, data["host_id"])
    if data.get("slug"):
        data["slug"] = check_slug_for_update(
            db, Podcasts, "podcast", data["slug"], podcast.id
        )
    required = {"title", "description", "slug", "topics", "notes", "is_published"}
    return crud.patch(db, podcast, data, required)


def delete_podcast(db: Session, podcast: Podcasts) -> None:
    crud.hard_delete(db, Podcasts, {"id": podcast.id})

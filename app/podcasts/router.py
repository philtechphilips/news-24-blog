from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.auth.dependencies import AdminUser
from app.core.database import DbSession
from app.core.slugs import SlugTakenError, UnknownReferenceError, to_http_error
from app.podcasts import service
from app.podcasts.models import Podcasts
from app.podcasts.schemas import PodcastCreate, PodcastResponse, PodcastUpdate

router = APIRouter(prefix="/podcasts", tags=["Podcasts"])

Limit = Annotated[int, Query(ge=1, le=100)]
Skip = Annotated[int, Query(ge=0)]


def _get_or_404(db: DbSession, podcast_id: UUID) -> Podcasts:
    podcast = service.get_podcast(db, podcast_id)
    if podcast is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Podcast with id {podcast_id} not found",
        )
    return podcast


@router.get("/", response_model=list[PodcastResponse])
def list_podcasts(db: DbSession, limit: Limit = 20, skip: Skip = 0):
    """Published episodes, newest first. Anyone can read these."""
    return service.list_published(db, limit, skip)


# Declared before /{podcast_id} so these aren't parsed as an id.
@router.get("/all", response_model=list[PodcastResponse])
def list_all_podcasts(db: DbSession, _: AdminUser, limit: Limit = 100, skip: Skip = 0):
    """Every episode including drafts, most recently updated first."""
    return service.list_all(db, limit, skip)


@router.get("/slug/{slug}", response_model=PodcastResponse)
def get_podcast_by_slug(slug: str, db: DbSession):
    podcast = service.get_published_by_slug(db, slug)
    if podcast is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Podcast {slug!r} not found"
        )
    return podcast


@router.get("/{podcast_id}", response_model=PodcastResponse)
def get_podcast(podcast_id: UUID, db: DbSession, _: AdminUser):
    return _get_or_404(db, podcast_id)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=PodcastResponse)
def create_podcast(body: PodcastCreate, db: DbSession, _: AdminUser):
    try:
        return service.create_podcast(db, body)
    except (SlugTakenError, UnknownReferenceError) as error:
        raise to_http_error(error) from None


@router.patch("/{podcast_id}", response_model=PodcastResponse)
def update_podcast(podcast_id: UUID, body: PodcastUpdate, db: DbSession, _: AdminUser):
    podcast = _get_or_404(db, podcast_id)
    try:
        return service.update_podcast(db, podcast, body)
    except (SlugTakenError, UnknownReferenceError) as error:
        raise to_http_error(error) from None


@router.delete("/{podcast_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_podcast(podcast_id: UUID, db: DbSession, _: AdminUser):
    service.delete_podcast(db, _get_or_404(db, podcast_id))

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Title = Annotated[str, Field(min_length=3, max_length=255)]
Slug = Annotated[str, Field(min_length=3, max_length=280)]
Description = Annotated[str, Field(min_length=1, max_length=1000)]
Url = Annotated[str, Field(max_length=500)]
Minutes = Annotated[int, Field(ge=1, le=1440)]


class PodcastCreate(BaseModel):
    title: Title
    description: Description
    # Generated from the title when left out
    slug: Slug | None = None
    cover_image: Url | None = None
    audio_url: Url | None = None
    duration_minutes: Minutes | None = None
    topics: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    is_published: bool = False
    host_id: UUID | None = None


class PodcastUpdate(BaseModel):
    title: Title | None = None
    description: Description | None = None
    slug: Slug | None = None
    cover_image: Url | None = None
    audio_url: Url | None = None
    duration_minutes: Minutes | None = None
    topics: list[str] | None = None
    notes: list[str] | None = None
    is_published: bool | None = None
    host_id: UUID | None = None


class PodcastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    description: str
    cover_image: str | None
    audio_url: str | None
    duration_minutes: int | None
    topics: list[str]
    notes: list[str]
    is_published: bool
    host_id: UUID | None
    created_at: datetime
    updated_at: datetime

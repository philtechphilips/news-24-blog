
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


PostTitle = Annotated[str, Field(min_length=3, max_length=255)]
PostSlug = Annotated[str, Field(min_length=3, max_length=280)]


class PostCreate(BaseModel):
    title: PostTitle
    body: str = Field(min_length=1)
    slug: PostSlug | None = None
    excerpt: str | None = None
    featured_image: str | None = None
    tags: list[str] = Field(default_factory=list)


class PostUpdate(BaseModel):
    title: PostTitle | None = None
    body: str | None = None
    slug: PostSlug | None = None
    excerpt: str | None = None
    featured_image: str | None = None
    tags: list[str] | None = None
    is_published: bool | None = None


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    body: str
    excerpt: str | None
    featured_image: str | None
    tags: list[str]
    is_published: bool
    created_at: datetime
    updated_at: datetime

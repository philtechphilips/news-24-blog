from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

PostTitle = Annotated[str, Field(min_length=3, max_length=255)]
PostSlug = Annotated[str, Field(min_length=3, max_length=280)]


class PostCreate(BaseModel):
    title: PostTitle
    body: str = Field(min_length=1)
    # Generated from the title when left out
    slug: PostSlug | None = None
    excerpt: str | None = Field(default=None, max_length=500)
    featured_image: str | None = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list)
    is_published: bool = False
    category_id: UUID | None = None


class PostUpdate(BaseModel):
    title: PostTitle | None = None
    body: str | None = Field(default=None, min_length=1)
    slug: PostSlug | None = None
    excerpt: str | None = Field(default=None, max_length=500)
    featured_image: str | None = Field(default=None, max_length=500)
    tags: list[str] | None = None
    is_published: bool | None = None
    category_id: UUID | None = None


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
    category_id: UUID | None
    created_at: datetime
    updated_at: datetime

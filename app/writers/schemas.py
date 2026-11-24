from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Name = Annotated[str, Field(min_length=2, max_length=255)]
Slug = Annotated[str, Field(min_length=2, max_length=280)]
Url = Annotated[str, Field(max_length=500)]
# Links shown on the writer's profile
Social = dict[Literal["x", "instagram", "linkedin"], Url]


class WriterCreate(BaseModel):
    name: Name
    role: Name
    # Generated from the name when left out
    slug: Slug | None = None
    avatar: Url | None = None
    location: str | None = Field(default=None, max_length=255)
    joined: date | None = None
    bio: list[str] = Field(default_factory=list)
    beats: list[str] = Field(default_factory=list)
    social: Social = Field(default_factory=dict)


class WriterUpdate(BaseModel):
    name: Name | None = None
    role: Name | None = None
    slug: Slug | None = None
    avatar: Url | None = None
    location: str | None = Field(default=None, max_length=255)
    joined: date | None = None
    bio: list[str] | None = None
    beats: list[str] | None = None
    social: Social | None = None


class WriterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    role: str
    avatar: str | None
    location: str | None
    joined: date | None
    bio: list[str]
    beats: list[str]
    social: dict[str, str]
    created_at: datetime
    updated_at: datetime

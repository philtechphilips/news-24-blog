from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, StringConstraints

CommentBody = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]


class CommentCreate(BaseModel):
    body: CommentBody
    # Set to reply to another comment on the same post
    parent_id: UUID | None = None


class CommentAuthor(BaseModel):
    id: UUID
    name: str


class CommentResponse(BaseModel):
    id: UUID
    post_id: UUID
    parent_id: UUID | None
    body: str
    created_at: datetime
    author: CommentAuthor
    likes: int = 0


class PostStats(BaseModel):
    likes: int
    comments: int
    shares: int


class Engagement(BaseModel):
    """Everything the comments section needs for one post."""

    stats: PostStats
    # Oldest first. Replies have a parent_id.
    comments: list[CommentResponse]
    # What the logged-in reader has liked (always empty for guests)
    liked: bool
    liked_comments: list[UUID]


class LikeResult(BaseModel):
    liked: bool
    likes: int

"""Comments, likes and shares on published posts, plus a live stream of them.

Reading is open to everyone; commenting and liking need a login; anyone can
share. Every change is pushed to the post's readers over GET /posts/{id}/live.
"""

from collections.abc import AsyncIterable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, OptionalUser
from app.core.database import DbSession, get_db
from app.core.slugs import UnknownReferenceError, to_http_error
from app.engagement import service
from app.engagement.live import READY, hub
from app.engagement.models import Comments
from app.engagement.schemas import (
    CommentCreate,
    CommentResponse,
    Engagement,
    LikeResult,
    PostStats,
)
from app.posts.models import Posts
from app.users.models import Role, User

router = APIRouter(tags=["Engagement"])


def _published_post(post_id: UUID, db: DbSession) -> Posts:
    post = service.get_published_post(db, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id {post_id} not found",
        )
    return post


def _comment(comment_id: UUID, db: DbSession) -> Comments:
    comment = service.get_comment(db, comment_id)
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment with id {comment_id} not found",
        )
    return comment


PublishedPost = Annotated[Posts, Depends(_published_post)]
PostComment = Annotated[Comments, Depends(_comment)]


def _publish_stats(db: Session, post: Posts) -> PostStats:
    stats = service.get_stats(db, post)
    hub.publish(post.id, "stats", stats.model_dump(mode="json"))
    return stats


# ---------- Reading ----------


@router.get("/posts/{post_id}/engagement", response_model=Engagement)
def get_engagement(post: PublishedPost, db: DbSession, viewer: OptionalUser):
    """Counts and every comment on a post, oldest first. Send a token to also
    get what you've liked (`liked`, `liked_comments`)."""
    return service.get_engagement(db, post, viewer)


def _check_live_post(
    post_id: UUID,
    # Function scope: the session closes once the post is checked instead of
    # staying open (holding a database connection) for the whole stream.
    db: Annotated[Session, Depends(get_db, scope="function")],
) -> None:
    _published_post(post_id, db)


@router.get(
    "/posts/{post_id}/live",
    response_class=EventSourceResponse,
    dependencies=[Depends(_check_live_post)],
)
async def live(post_id: UUID) -> AsyncIterable[ServerSentEvent]:
    """Server-Sent Events for everything that happens on a post. Each event's
    `data` is JSON:

    - `ready` `{}`: sent when you connect (and if you fall behind). Load
      GET /posts/{id}/engagement now; events after this keep it current.
    - `comment`: a new comment or reply, shaped like the engagement comments
    - `comment_removed` `{"ids": [...]}`: a comment and its replies were deleted
    - `comment_like` `{"comment_id", "likes", "user_id", "liked"}`
    - `post_like` `{"user_id", "liked"}`: so that reader's other tabs update
    - `stats` `{"likes", "comments", "shares"}`: the post's new totals

    A `: ping` comment every 15 seconds keeps idle connections open.
    """
    async with hub.subscribe(post_id) as queue:
        event, data = READY
        # `retry`: how long browsers wait before reconnecting after a drop.
        yield ServerSentEvent(event=event, data=data, retry=3000)
        while True:
            event, data = await queue.get()
            yield ServerSentEvent(event=event, data=data)


# ---------- Comments ----------


@router.post(
    "/posts/{post_id}/comments",
    status_code=status.HTTP_201_CREATED,
    response_model=CommentResponse,
)
def add_comment(
    body: CommentCreate, post: PublishedPost, db: DbSession, user: CurrentUser
):
    """Comment on a post, or reply to a comment with `parent_id`."""
    try:
        comment = service.create_comment(db, post, user, body)
    except UnknownReferenceError as error:
        raise to_http_error(error) from None
    hub.publish(post.id, "comment", comment.model_dump(mode="json"))
    _publish_stats(db, post)
    return comment


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment: PostComment, db: DbSession, user: CurrentUser):
    """Delete a comment and its replies. Only its author or an admin can."""
    if comment.author_id != user.id and user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments",
        )
    post_id = comment.post_id
    ids = service.delete_comment(db, comment)
    hub.publish(post_id, "comment_removed", {"ids": [str(i) for i in ids]})
    post = service.get_published_post(db, post_id)
    if post is not None:
        _publish_stats(db, post)


# ---------- Likes ----------


def _like_post(db: Session, post: Posts, user: User, liked: bool):
    result = service.like_post(db, post, user, liked)
    hub.publish(post.id, "post_like", {"user_id": str(user.id), "liked": liked})
    _publish_stats(db, post)
    return result


@router.put("/posts/{post_id}/like", response_model=LikeResult)
def like_post(post: PublishedPost, db: DbSession, user: CurrentUser):
    """Like a post. Liking twice is fine; it still counts once."""
    return _like_post(db, post, user, True)


@router.delete("/posts/{post_id}/like", response_model=LikeResult)
def unlike_post(post: PublishedPost, db: DbSession, user: CurrentUser):
    return _like_post(db, post, user, False)


def _like_comment(db: Session, comment: Comments, user: User, liked: bool):
    result = service.like_comment(db, comment, user, liked)
    hub.publish(
        comment.post_id,
        "comment_like",
        {
            "comment_id": str(comment.id),
            "likes": result.likes,
            "user_id": str(user.id),
            "liked": liked,
        },
    )
    return result


@router.put("/comments/{comment_id}/like", response_model=LikeResult)
def like_comment(comment: PostComment, db: DbSession, user: CurrentUser):
    return _like_comment(db, comment, user, True)


@router.delete("/comments/{comment_id}/like", response_model=LikeResult)
def unlike_comment(comment: PostComment, db: DbSession, user: CurrentUser):
    return _like_comment(db, comment, user, False)


# ---------- Shares ----------


@router.post("/posts/{post_id}/share", response_model=PostStats)
def share_post(post: PublishedPost, db: DbSession):
    """Count a share (copied link, X, WhatsApp...). No login needed."""
    stats = service.share_post(db, post)
    hub.publish(post.id, "stats", stats.model_dump(mode="json"))
    return stats

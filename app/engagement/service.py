from collections import defaultdict
from uuid import UUID

from sqlalchemy import ColumnElement, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import crud
from app.core.slugs import UnknownReferenceError
from app.engagement.models import CommentLikes, Comments, PostLikes
from app.engagement.schemas import (
    CommentAuthor,
    CommentCreate,
    CommentResponse,
    Engagement,
    LikeResult,
    PostStats,
)
from app.posts.models import Posts
from app.users.models import User

# Shown for readers who haven't set a display name.
UNNAMED = "Reader"


def get_published_post(db: Session, post_id: UUID) -> Posts | None:
    return crud.fetch_one(db, Posts, {"id": post_id, "is_published": True})


def get_comment(db: Session, comment_id: UUID) -> Comments | None:
    """A comment on a published post."""
    return crud.fetch_one(
        db,
        Comments,
        {"id": comment_id},
        join=[(Posts, Posts.id == Comments.post_id)],
        where=[Posts.is_published.is_(True)],
    )


def get_stats(db: Session, post: Posts) -> PostStats:
    return PostStats(
        likes=crud.count_items(db, PostLikes, {"post_id": post.id}),
        comments=crud.count_items(db, Comments, {"post_id": post.id}),
        shares=post.share_count,
    )


def _to_response(comment: Comments, likes: int = 0) -> CommentResponse:
    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        parent_id=comment.parent_id,
        body=comment.body,
        created_at=comment.created_at,
        author=CommentAuthor(id=comment.author.id, name=comment.author.name or UNNAMED),
        likes=likes,
    )


def _on_post(post: Posts) -> ColumnElement[bool]:
    """CommentLikes rows that belong to this post's comments."""
    return CommentLikes.comment_id.in_(
        select(Comments.id).where(Comments.post_id == post.id)
    )


def get_engagement(db: Session, post: Posts, viewer: User | None) -> Engagement:
    comments = crud.fetch(
        db,
        Comments,
        {"post_id": post.id},
        populate=["author"],
        order_by=[Comments.created_at, Comments.id],
    )
    likes = dict(
        crud.aggregate(
            db,
            CommentLikes,
            columns=[CommentLikes.comment_id, func.count()],
            group_by=[CommentLikes.comment_id],
            where=[_on_post(post)],
        )
    )
    liked, liked_comments = False, []
    if viewer is not None:
        mine = {"post_id": post.id, "user_id": viewer.id}
        liked = crud.fetch_one(db, PostLikes, mine) is not None
        liked_comments = [
            like.comment_id
            for like in crud.simple_list(
                db, CommentLikes, {"user_id": viewer.id}, where=[_on_post(post)]
            )
        ]
    return Engagement(
        stats=get_stats(db, post),
        comments=[_to_response(c, likes.get(c.id, 0)) for c in comments],
        liked=liked,
        liked_comments=liked_comments,
    )


def create_comment(
    db: Session, post: Posts, author: User, comment_in: CommentCreate
) -> CommentResponse:
    parent_id = comment_in.parent_id
    if parent_id and not crud.fetch_one(
        db, Comments, {"id": parent_id, "post_id": post.id}
    ):
        raise UnknownReferenceError("comment", parent_id)
    comment = crud.create(
        db,
        Comments,
        {
            "post_id": post.id,
            "author_id": author.id,
            "parent_id": parent_id,
            "body": comment_in.body,
        },
    )
    return _to_response(comment)


def delete_comment(db: Session, comment: Comments) -> list[UUID]:
    """Delete a comment and every reply under it. Returns all their ids."""
    replies: dict[UUID | None, list[UUID]] = defaultdict(list)
    for c in crud.simple_list(db, Comments, {"post_id": comment.post_id}):
        replies[c.parent_id].append(c.id)
    ids = [comment.id]
    for comment_id in ids:  # grows as it goes, walking down the thread
        ids.extend(replies[comment_id])
    # Their likes go too (ON DELETE CASCADE).
    crud.hard_delete_many(db, Comments, where=[Comments.id.in_(ids)])
    return ids


def _set_like(db: Session, model: type, key: dict[str, UUID], liked: bool) -> None:
    if not liked:
        crud.hard_delete_many(db, model, key)
    elif crud.fetch_one(db, model, key) is None:
        try:
            crud.create(db, model, key)
        except IntegrityError:
            db.rollback()  # A second click got there first; it's liked either way.


def like_post(db: Session, post: Posts, user: User, liked: bool) -> LikeResult:
    _set_like(db, PostLikes, {"post_id": post.id, "user_id": user.id}, liked)
    likes = crud.count_items(db, PostLikes, {"post_id": post.id})
    return LikeResult(liked=liked, likes=likes)


def like_comment(db: Session, comment: Comments, user: User, liked: bool) -> LikeResult:
    _set_like(db, CommentLikes, {"comment_id": comment.id, "user_id": user.id}, liked)
    likes = crud.count_items(db, CommentLikes, {"comment_id": comment.id})
    return LikeResult(liked=liked, likes=likes)


def share_post(db: Session, post: Posts) -> PostStats:
    # Incremented in the database, so simultaneous shares all count.
    db.execute(
        update(Posts)
        .where(Posts.id == post.id)
        .values(share_count=Posts.share_count + 1)
    )
    db.commit()
    db.refresh(post)
    return get_stats(db, post)

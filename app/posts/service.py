from uuid import UUID

from sqlalchemy import case, or_
from sqlalchemy.orm import Query, Session

from app.categories.models import Categories
from app.core import crud
from app.core.slugs import (
    UnknownReferenceError,
    check_slug_for_update,
    slug_for_create,
)
from app.posts.models import Posts
from app.posts.schemas import PostCreate, PostUpdate
from app.writers.models import Writers


def _check_refs(db: Session, data: dict) -> None:
    """The category and writer a post points at must exist."""
    for key, model, kind in (
        ("category_id", Categories, "category"),
        ("writer_id", Writers, "writer"),
    ):
        ref_id = data.get(key)
        if ref_id and crud.fetch_one(db, model, {"id": ref_id}) is None:
            raise UnknownReferenceError(kind, ref_id)


def _like(text: str) -> str:
    """A LIKE pattern matching `text` literally (so % and _ aren't wildcards)."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _published_query(
    db: Session, category_id: UUID | None, writer_id: UUID | None, q: str | None
) -> tuple[Query[Posts], list]:
    """The filtered query for published posts, and the order to list them in."""
    query = db.query(Posts).filter(Posts.is_published.is_(True))
    if category_id:
        query = query.filter(Posts.category_id == category_id)
    if writer_id:
        query = query.filter(Posts.writer_id == writer_id)

    order = [Posts.created_at.desc()]
    words = (q or "").split()
    if words:
        query = query.outerjoin(Categories, Posts.category_id == Categories.id)
        for word in words:
            pattern = _like(word)
            query = query.filter(
                or_(
                    *(
                        column.ilike(pattern, escape="\\")
                        for column in (
                            Posts.title,
                            Posts.excerpt,
                            Posts.body,
                            Categories.name,
                        )
                    )
                )
            )
        in_title = Posts.title.ilike(_like(" ".join(words)), escape="\\")
        order.insert(0, case((in_title, 0), else_=1))
    return query, order


def list_published(
    db: Session,
    category_id: UUID | None = None,
    writer_id: UUID | None = None,
    q: str | None = None,
    limit: int = 20,
    skip: int = 0,
) -> tuple[list[Posts], int]:
    """One page of published posts, newest first, and how many match in total.
    With `q`, only posts where every word appears in the title, excerpt, body
    or category name; title matches come first."""
    query, order = _published_query(db, category_id, writer_id, q)
    total = query.count()
    return query.order_by(*order).offset(skip).limit(limit).all(), total


def list_all(db: Session, limit: int = 100, skip: int = 0) -> list[Posts]:
    return crud.fetch(db, Posts, sort_by="updated_at", limit=limit, skip=skip)


def get_post(db: Session, post_id: UUID) -> Posts | None:
    return crud.fetch_one(db, Posts, {"id": post_id})


def get_published_by_slug(db: Session, slug: str) -> Posts | None:
    return crud.fetch_one(db, Posts, {"slug": slug, "is_published": True})


def create_post(db: Session, post_in: PostCreate) -> Posts:
    data = post_in.model_dump()
    _check_refs(db, data)
    data["slug"] = slug_for_create(db, Posts, "post", data["slug"], data["title"])
    return crud.create(db, Posts, data)


def update_post(db: Session, post: Posts, post_in: PostUpdate) -> Posts:
    # Only the fields the client sent, so optional ones can be cleared with null.
    data = post_in.model_dump(exclude_unset=True)
    _check_refs(db, data)
    if data.get("slug"):
        data["slug"] = check_slug_for_update(db, Posts, "post", data["slug"], post.id)
    required = {"title", "body", "slug", "tags", "is_published"}
    return crud.patch(db, post, data, required)


def delete_post(db: Session, post: Posts) -> None:
    crud.hard_delete(db, Posts, {"id": post.id})

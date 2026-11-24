import re
import unicodedata
from uuid import UUID

from sqlalchemy.orm import Session

from app.categories.models import Categories
from app.core import crud
from app.posts.models import Posts
from app.posts.schemas import PostCreate, PostUpdate


class SlugTakenError(Exception):
    def __init__(self, slug: str):
        super().__init__(f"A post with slug {slug!r} already exists")


class UnknownCategoryError(Exception):
    def __init__(self, category_id: UUID):
        super().__init__(f"Category with id {category_id} not found")


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:270].strip("-") or "post"


def _slug_taken(db: Session, slug: str, exclude_id: UUID | None = None) -> bool:
    post = crud.fetch_one(db, Posts, {"slug": slug})
    return post is not None and post.id != exclude_id


def _unique_slug(db: Session, base: str) -> str:
    slug, n = base, 2
    while _slug_taken(db, slug):
        slug, n = f"{base}-{n}", n + 1
    return slug


def _check_category(db: Session, category_id: UUID | None) -> None:
    if category_id and crud.fetch_one(db, Categories, {"id": category_id}) is None:
        raise UnknownCategoryError(category_id)


def list_published(
    db: Session, category_id: UUID | None = None, limit: int = 20, skip: int = 0
) -> list[Posts]:
    filters: dict = {"is_published": True}
    if category_id:
        filters["category_id"] = category_id
    return crud.fetch(db, Posts, filters, limit=limit, skip=skip)


def list_all(db: Session, limit: int = 100, skip: int = 0) -> list[Posts]:
    return crud.fetch(db, Posts, sort_by="updated_at", limit=limit, skip=skip)


def get_post(db: Session, post_id: UUID) -> Posts | None:
    return crud.fetch_one(db, Posts, {"id": post_id})


def get_published_by_slug(db: Session, slug: str) -> Posts | None:
    return crud.fetch_one(db, Posts, {"slug": slug, "is_published": True})


def create_post(db: Session, post_in: PostCreate) -> Posts:
    data = post_in.model_dump()
    _check_category(db, data["category_id"])
    if data["slug"]:
        data["slug"] = slugify(data["slug"])
        if _slug_taken(db, data["slug"]):
            raise SlugTakenError(data["slug"])
    else:
        data["slug"] = _unique_slug(db, slugify(data["title"]))
    return crud.create(db, Posts, data)


# Columns that can't be cleared; a null for these in a PATCH is ignored.
_REQUIRED = {"title", "body", "slug", "tags", "is_published"}


def update_post(db: Session, post: Posts, post_in: PostUpdate) -> Posts:
    # Only the fields the client sent, so optional ones can be cleared with null.
    data = post_in.model_dump(exclude_unset=True)
    data = {k: v for k, v in data.items() if v is not None or k not in _REQUIRED}
    if "category_id" in data:
        _check_category(db, data["category_id"])
    if "slug" in data:
        data["slug"] = slugify(data["slug"])
        if _slug_taken(db, data["slug"], exclude_id=post.id):
            raise SlugTakenError(data["slug"])
    for key, value in data.items():
        setattr(post, key, value)
    db.commit()
    db.refresh(post)
    return post


def delete_post(db: Session, post: Posts) -> None:
    crud.hard_delete(db, Posts, {"id": post.id})

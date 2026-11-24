"""Load the sample categories and posts from seed/posts.json.

uv run poe seed

Safe to run more than once: categories that already exist (by name) and posts
that already exist (by slug) are skipped, so nothing is duplicated.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.categories.models import Categories
from app.core.database import SessionLocal
from app.posts.models import Posts

SEED_FILE = Path(__file__).resolve().parent.parent / "seed" / "posts.json"


def seed(db: Session, data: dict[str, Any]) -> tuple[int, int]:
    """Insert what's missing. Returns (categories added, posts added)."""
    categories = {c.name: c for c in db.query(Categories).all()}
    added_categories = 0
    for name in data["categories"]:
        if name not in categories:
            categories[name] = Categories(name=name)
            db.add(categories[name])
            added_categories += 1
    db.flush()  # gives the new categories their ids

    existing_slugs = {slug for (slug,) in db.query(Posts.slug)}
    added_posts = 0
    for item in data["posts"]:
        if item["slug"] in existing_slugs:
            continue
        # Keep the original publish date so the newest-first order makes sense.
        when = datetime.fromisoformat(item["date"]).replace(hour=9, tzinfo=UTC)
        category = categories.get(item["category"])
        db.add(
            Posts(
                title=item["title"],
                slug=item["slug"],
                body=item["body"],
                excerpt=item["excerpt"],
                featured_image=item["featured_image"],
                tags=item["tags"],
                is_published=item["is_published"],
                category_id=category.id if category else None,
                created_at=when,
                updated_at=when,
            )
        )
        added_posts += 1

    db.commit()
    return added_categories, added_posts


def main() -> None:
    data = json.loads(SEED_FILE.read_text())
    with SessionLocal() as db:
        categories, posts = seed(db, data)
    print(f"Added {categories} categories and {posts} posts (existing ones skipped)")


if __name__ == "__main__":
    main()

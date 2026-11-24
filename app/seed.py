"""Load the sample writers, categories, posts and podcasts from seed/*.json.

uv run poe seed

Safe to run more than once: rows that already exist (writers, posts and
podcasts by slug, categories by name) are skipped, so nothing is duplicated.
Existing posts and podcasts without an author get one filled in.
"""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.categories.models import Categories
from app.core.database import SessionLocal
from app.podcasts.models import Podcasts
from app.posts.models import Posts
from app.writers.models import Writers

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"


def load_seed_data() -> dict[str, Any]:
    data: dict[str, Any] = {}
    for name in ("writers", "posts", "podcasts"):
        data |= json.loads((SEED_DIR / f"{name}.json").read_text())
    return data


def _published_at(day: str) -> datetime:
    # Keep the original date so newest-first order makes sense.
    return datetime.fromisoformat(day).replace(hour=9, tzinfo=UTC)


def seed(db: Session, data: dict[str, Any]) -> dict[str, int]:
    """Insert what's missing. Returns how many of each were added."""
    added = {"writers": 0, "categories": 0, "posts": 0, "podcasts": 0}

    writers = {w.slug: w for w in db.query(Writers).all()}
    # Spaced a minute apart so the list keeps the file's order (oldest first).
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for i, item in enumerate(data["writers"]):
        if item["slug"] in writers:
            continue
        joined = date.fromisoformat(item["joined"]) if item.get("joined") else None
        writers[item["slug"]] = Writers(
            **{k: item.get(k) for k in ("name", "slug", "role", "avatar", "location")},
            joined=joined,
            bio=item["bio"],
            beats=item["beats"],
            social=item["social"],
            created_at=start + timedelta(minutes=i),
            updated_at=start + timedelta(minutes=i),
        )
        db.add(writers[item["slug"]])
        added["writers"] += 1

    categories = {c.name: c for c in db.query(Categories).all()}
    for name in data["categories"]:
        if name not in categories:
            categories[name] = Categories(name=name)
            db.add(categories[name])
            added["categories"] += 1
    db.flush()  # gives the new writers and categories their ids

    def writer_id(slug: str | None):
        return writers[slug].id if slug in writers else None

    posts = {p.slug: p for p in db.query(Posts).all()}
    for item in data["posts"]:
        if item["slug"] in posts:
            existing = posts[item["slug"]]
            if existing.writer_id is None:
                existing.writer_id = writer_id(item.get("writer"))
            continue
        category = categories.get(item["category"])
        when = _published_at(item["date"])
        db.add(
            Posts(
                **{
                    k: item[k]
                    for k in ("title", "slug", "body", "excerpt", "featured_image")
                },
                tags=item["tags"],
                is_published=item["is_published"],
                category_id=category.id if category else None,
                writer_id=writer_id(item.get("writer")),
                created_at=when,
                updated_at=when,
            )
        )
        added["posts"] += 1

    podcasts = {p.slug: p for p in db.query(Podcasts).all()}
    for item in data["podcasts"]:
        if item["slug"] in podcasts:
            existing = podcasts[item["slug"]]
            if existing.host_id is None:
                existing.host_id = writer_id(item.get("host"))
            continue
        when = _published_at(item["date"])
        db.add(
            Podcasts(
                **{k: item[k] for k in ("title", "slug", "description", "cover_image")},
                duration_minutes=item["duration_minutes"],
                topics=item["topics"],
                notes=item["notes"],
                is_published=item["is_published"],
                host_id=writer_id(item.get("host")),
                created_at=when,
                updated_at=when,
            )
        )
        added["podcasts"] += 1

    db.commit()
    return added


def main() -> None:
    with SessionLocal() as db:
        added = seed(db, load_seed_data())
    summary = ", ".join(f"{count} {name}" for name, count in added.items())
    print(f"Added {summary} (existing ones skipped)")


if __name__ == "__main__":
    main()

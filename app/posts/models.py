import uuid
from datetime import datetime

from sqlalchemy import JSON, TIMESTAMP, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Posts(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(280), unique=True, index=True)
    body: Mapped[str] = mapped_column(Text)
    excerpt: Mapped[str | None] = mapped_column(String(500))
    featured_image: Mapped[str | None] = mapped_column(String(500))
    # JSON rather than a Postgres ARRAY so the SQLite test database works too.
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_published: Mapped[bool] = mapped_column(default=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    # The byline. Deleting the writer keeps the post, without an author.
    writer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("writers.id", ondelete="SET NULL"), index=True
    )
    # Bumped each time a reader shares the post (copy link, X, WhatsApp...).
    share_count: Mapped[int] = mapped_column(server_default="0", default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

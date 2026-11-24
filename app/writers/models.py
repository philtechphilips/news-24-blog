import uuid
from datetime import date, datetime

from sqlalchemy import JSON, TIMESTAMP, Date, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Writers(Base):
    """Staff writers shown on the site. Not login accounts."""

    __tablename__ = "writers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(280), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(255))
    avatar: Mapped[str | None] = mapped_column(String(500))
    location: Mapped[str | None] = mapped_column(String(255))
    joined: Mapped[date | None] = mapped_column(Date)
    # Paragraphs of the bio, topics they cover, and links like {"x": "https://..."}
    bio: Mapped[list[str]] = mapped_column(JSON, default=list)
    beats: Mapped[list[str]] = mapped_column(JSON, default=list)
    social: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

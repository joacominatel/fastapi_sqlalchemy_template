from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timezone import aware_now
from app.db.base import Base


class User(Base):
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=aware_now,
        nullable=False,
        index=True,  # Index for efficient ordering in list queries
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=aware_now,
        onupdate=aware_now,
        nullable=False,
    )


__all__ = ["User"]

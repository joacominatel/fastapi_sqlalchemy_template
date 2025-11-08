from __future__ import annotations

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserBase(BaseModel):
    email: EmailStr = Field(max_length=255)
    is_active: bool = True


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCollection(BaseModel):
    items: list[UserRead]
    total: int
    limit: int
    offset: int

    model_config = ConfigDict(from_attributes=True)

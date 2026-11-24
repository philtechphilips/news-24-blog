import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.users.models import Role

Password = Annotated[str, Field(min_length=8, max_length=128)]
DisplayName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)
]


class UserCreate(BaseModel):
    email: EmailStr
    password: Password
    # The name shown on their comments
    name: DisplayName | None = None


class ProfileUpdate(BaseModel):
    name: DisplayName


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    name: str | None
    role: Role
    created_at: datetime


class RoleUpdate(BaseModel):
    role: Role

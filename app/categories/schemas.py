from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

CategoryName = Annotated[str, Field(min_length=2, max_length=255)]


class CategoryCreate(BaseModel):
    name: CategoryName


class CategoryUpdate(BaseModel):
    name: CategoryName | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime

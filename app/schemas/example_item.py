from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExampleItemCreate(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None


class ExampleItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class ExampleItemRead(BaseModel):
    id: UUID
    key: str
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

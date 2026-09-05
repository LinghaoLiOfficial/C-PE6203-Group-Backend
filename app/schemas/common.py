from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

DataT = TypeVar("DataT")


class ApiStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"


class ErrorResponse(BaseModel):
    error: str
    code: str
    details: dict | list | str | None = None


class ApiResponse(BaseModel, Generic[DataT]):
    status: ApiStatus = ApiStatus.SUCCESS
    data: DataT
    message: str | None = None


class PaginationMeta(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class PaginatedResponse(BaseModel, Generic[DataT]):
    items: list[DataT]
    pagination: PaginationMeta


class MessageResponse(BaseModel):
    message: str

    model_config = ConfigDict(from_attributes=True)

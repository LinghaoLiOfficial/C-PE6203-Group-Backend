from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession
from app.crud.example_item import create_item, delete_item, get_item, list_items, update_item
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.schemas.example_item import ExampleItemCreate, ExampleItemRead, ExampleItemUpdate

router = APIRouter(prefix="/example-items")


@router.get("", response_model=ApiResponse[PaginatedResponse[ExampleItemRead]])
def list_example_items(
    db: DbSession, page: int = 1, page_size: int = 20
) -> ApiResponse[PaginatedResponse[ExampleItemRead]]:
    if page < 1 or not 1 <= page_size <= 100:
        raise HTTPException(
            status_code=422, detail="page must be >= 1 and page_size must be between 1 and 100"
        )
    items, total = list_items(db, offset=(page - 1) * page_size, limit=page_size)
    return ApiResponse(
        data=PaginatedResponse(
            items=items,
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=(total + page_size - 1) // page_size,
            ),
        )
    )


@router.post("", response_model=ApiResponse[ExampleItemRead], status_code=status.HTTP_201_CREATED)
def create_example_item(db: DbSession, payload: ExampleItemCreate) -> ApiResponse[ExampleItemRead]:
    try:
        return ApiResponse(data=create_item(db, payload))
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="key already exists") from exc


@router.get("/{item_id}", response_model=ApiResponse[ExampleItemRead])
def get_example_item(db: DbSession, item_id: UUID) -> ApiResponse[ExampleItemRead]:
    item = get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="example item not found")
    return ApiResponse(data=item)


@router.patch("/{item_id}", response_model=ApiResponse[ExampleItemRead])
def patch_example_item(
    db: DbSession, item_id: UUID, payload: ExampleItemUpdate
) -> ApiResponse[ExampleItemRead]:
    item = get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="example item not found")
    return ApiResponse(data=update_item(db, item, payload))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_example_item(db: DbSession, item_id: UUID) -> None:
    item = get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="example item not found")
    delete_item(db, item)

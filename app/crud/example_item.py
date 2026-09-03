from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.example_item import ExampleItem
from app.schemas.example_item import ExampleItemCreate, ExampleItemUpdate


def list_items(db: Session, *, offset: int, limit: int) -> tuple[list[ExampleItem], int]:
    total = db.scalar(select(func.count()).select_from(ExampleItem)) or 0
    items = list(
        db.scalars(
            select(ExampleItem).order_by(ExampleItem.created_at.desc()).offset(offset).limit(limit)
        )
    )
    return items, total


def get_item(db: Session, item_id: UUID) -> ExampleItem | None:
    return db.get(ExampleItem, item_id)


def create_item(db: Session, payload: ExampleItemCreate) -> ExampleItem:
    item = ExampleItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(db: Session, item: ExampleItem, payload: ExampleItemUpdate) -> ExampleItem:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item: ExampleItem) -> None:
    db.delete(item)
    db.commit()

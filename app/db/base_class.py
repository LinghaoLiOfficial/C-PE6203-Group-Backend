from sqlalchemy import DDL, event
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


event.listen(Base.metadata, "before_create", DDL("CREATE EXTENSION IF NOT EXISTS vector"))

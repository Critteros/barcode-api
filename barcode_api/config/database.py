import datetime
from typing import AsyncGenerator
from functools import cache

from pydantic import UUID4
from sqlalchemy import TIMESTAMP, UUID, func, text
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

from barcode_api.config.settings import get_database_url


class Base(AsyncAttrs, DeclarativeBase):
    """
    Base class for all models. Inherits from `AsyncAttrs` and `DeclarativeBase`.

    Attributes:
        None

    Methods:
        __tablename__(cls) -> str: Returns the name of the table for the model.

    Usage:
        To use this class, import `Base` and inherit from it to create a new model:

        ```
        from barcode_api.config.database import Base
        from sqlalchemy import Column, Integer, String

        class MyModel(Base):
            __tablename__ = "my_table"

            id = Column(Integer, primary_key=True, index=True)
            name = Column(String, index=True)
            description = Column(String, index=True)
        ```
    """

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__


class SequentialIdMixin:
    """
    Mixins used for model to have sequential id.

    Attributes:
        id (Mapped[int]): An integer primary key that auto-increments.

    Methods:
        __repr__(self) -> str: Returns a string representation of the object.

    """

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"


class UUIDMixin:
    """
    Mixin used for model to have UUID id.

    Attributes:
        id (Mapped[UUID4]): A UUID primary key that is generated using uuid_generate_v4().

    Methods:
        __repr__(self) -> str: Returns a string representation of the object.

    """

    id: Mapped[UUID4] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"), unique=True, nullable=False
    )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"


class CreatedAtUpdatedAtMixin:
    """
    A mixin that provides `created_at` and `updated_at` fields to a model.

    Attributes:
        created_at (datetime): The date and time when the object was created.
        updated_at (datetime): The date and time when the object was last updated.
    """

    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


@cache
def get_sessionmaker():
    engine = create_async_engine(
        get_database_url(),
        future=True,
        echo=False,
        pool_size=10,
        max_overflow=10,
        isolation_level="SERIALIZABLE",
    )

    AsyncDBSession = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    return AsyncDBSession


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    A aync generator that yields an asynchronous database session.

    Yields:
        AsyncSession: An asynchronous database session.

    Example:
        Depends(db_session)
    """
    AsyncDBSession = get_sessionmaker()
    async with AsyncDBSession() as session:
        yield session

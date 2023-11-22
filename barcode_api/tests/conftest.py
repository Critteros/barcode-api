import os
from typing import AsyncGenerator, Generator

import pytest
import asyncio
import pytest_asyncio
from httpx import AsyncClient
from fastapi import FastAPI
from alembic.config import Config
from alembic.command import upgrade, downgrade
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer
from unittest.mock import Mock

from barcode_api.config.settings import settings

from barcode_api.schemas.token import OIDCToken
from barcode_api.models.product import Product
from .types import MockImage
from .utils import random_image, build_oidc_token, random_product


@pytest.fixture(scope="function")
def app() -> Generator[FastAPI, None, None]:
    # This will load application config which can crash test if the config is not mocked
    from barcode_api.app import app as _app

    original_dependency_overrides = _app.dependency_overrides
    _app.dependency_overrides = original_dependency_overrides.copy()

    yield _app

    _app.dependency_overrides = original_dependency_overrides


@pytest.fixture(scope="session")
def base_url() -> str:
    return "http://testserver"


@pytest_asyncio.fixture(scope="function")
async def client(base_url: str, app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url=base_url) as client:
        yield client


@pytest.fixture(scope="session")
def database_url(session_mocker: Mock) -> str:
    with PostgresContainer("postgres:16") as postgres:
        url = postgres.get_connection_url().replace("psycopg2", "psycopg")
        settings.SQLALCHEMY_DATABASE_URI = url
        session_mocker.patch("barcode_api.config.database.get_database_url", return_value=url)
        yield url


@pytest.fixture(scope="session", autouse=True)
def apply_migrations(database_url: str) -> Generator[None, None, None]:
    os.environ["TESTING"] = "1"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    upgrade(config, "head")
    yield
    downgrade(config, "base")


@pytest.fixture(scope="session")
def event_loop():
    """Overrides pytest default function scoped event loop"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="class")
def image() -> MockImage:
    return random_image(width=100, height=100)


@pytest_asyncio.fixture(scope="session")
@pytest.mark.usefixtures("apply_migrations")
async def session(database_url) -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        database_url,
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

    async with AsyncDBSession() as session:
        yield session


@pytest.fixture(scope="function")
def token(request: pytest.FixtureRequest) -> OIDCToken:
    marker = request.node.get_closest_marker("roles")

    params = {}
    if marker is not None:
        params["roles"] = marker.args[0]

    marker = request.node.get_closest_marker("scopes")
    if marker is not None:
        params["scopes"] = marker.args[0]

    return build_oidc_token(**params)


@pytest.fixture(scope="function")
def products(request: pytest.FixtureRequest) -> list[Product]:
    marker = request.node.get_closest_marker("num_products")

    if marker is not None:
        return [random_product() for _ in range(marker.args[0])]

    return [random_product() for _ in range(10)]

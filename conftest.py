"""Общие фикстуры для всех тестов"""
import dataclasses
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Generator, ParamSpecKwargs
from uuid import UUID, uuid4

import pydantic
import pytest
import sqlalchemy as sa
import starlette.requests
from dishka import AsyncContainer, Provider, Scope, make_async_container
from httpx import AsyncClient
from loguru import logger
from pytest_mock import MockerFixture
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    AsyncTransaction,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

import pytest
from unittest.mock import AsyncMock, MagicMock, create_autospec
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.transaction import Transaction
from src.core.configs import AdminSettings, AuthSettings, FileSettings, PostgresSettings, SQLEngineSettings, settings
from src.core.containers import get_providers
from src.infrastructure.postgres.models.base import BaseORM
from src.infrastructure.postgres.transaction import SQLAlchemyTransaction

log = logger.info

# To run async tests
# pytestmark = pytest.mark.anyio


# Required per https://anyio.readthedocs.io/en/stable/testing.html#using-async-fixtures-with-higher-scopes
@pytest.fixture(scope="session")
def anyio_backend():
    """Без этой фикстуры не работают асинхронные тесты.

    Чтобы в тестах можно было await'ить асинхронные функции ...
    (неправильно их называть корутинами - они фабрики корутин),
    нужно объявлять сами тестовые функции/методы асинхронными и
    маркировать их декоратором (хотя, кажется, и декоратором маркировать не нужно):

    @pytest.mark.anyio
    # @pytest.mark.asyncio  # или так - вариант от claude
    class TestCreateCountryInteractor:

        # асинхронный тест-метод!!
        async def test_call(self, dishka_container, country_query, mocker):
            ...
            # вызываем асинхронный код без "ручного" заворачивания в asyncio-таску
            interactor = await dishka_container.get(CreateCountryInteractor)
    """
    return "asyncio"


@pytest.fixture
def mock_model():
    """Фикстура для мока моделей.

    Позволяет задать только минимально необходимые атрибуты для акцента на конкретной логике.
    Мок-объект можно использовать, не беспокоясь об ошибках от pydantic и dataclass про недостающие атрибуты.

    Пример использования:

    ```
        @pytest.fixture
        def country_query(mock_model):
            return mock_model(
                CountryQueryModel,
                code='YY',
                name='YY Country',
                image_path="country/yy.png",
            )


        @pytest.fixture
        def country(mock_model):
            return mock_model(CountryORM)


        @pytest.mark.anyio
        class TestMockModels:
            async def test_models(self, country_query):
                c1 = country_query()
                c2 = country_query(
                    code='YY',
                    name='YY Country',
                    image_path="country/yy.png",
                )
                assert c1.code == c2.code
                assert c1.name == c2.name
                assert c1.image_path == c2.image_path

                assert c2.code == 'YY'
                assert c2.name == 'YY Country'
                assert c2.image_path == "country/yy.png"

                c3 = country_query(name='AB')
                assert c1.code == c3.code
                assert c1.image_path == c3.image_path

                assert c3.name == 'AB'

                with pytest.raises(AttributeError):
                    c3.ook = 'ook'

            async def test_country_model(self, country):
                c1 = country(
                    code='YY',
                    name='YY Country',
                    # image_path не передан!
                )
                assert c1.code == 'YY'
                assert c1.name == 'YY Country'
    ```

    """
    def _fixture(
        model_class: type[dataclasses.dataclass] | pydantic.BaseModel,
        **default_fields: ParamSpecKwargs,
    ):
        def _model_factory(**kwargs):
            mock = create_autospec(model_class, spec_set=True)
            # ← обычные значения, чтобы не генерировались mock-атрибуты
            # for key, value in kwargs.items():
            #     setattr(mock, key, value)
            mock.__dict__.update(default_fields)
            mock.__dict__.update(kwargs)
            return mock
        return _model_factory
    return _fixture


# @pytest.fixture  # не имеет смысла
# def mock_session() -> AsyncSession:
#     """Мок SQLAlchemy сессии"""
#     session = MagicMock(spec=AsyncSession)
#     session.execute = AsyncMock()
#     session.commit = AsyncMock()
#     session.rollback = AsyncMock()
#     session.close = AsyncMock()
#     return session


@pytest.fixture
def mock_request() -> starlette.requests.Request:
    """Мок FastAPI Request"""
    request = MagicMock(spec=starlette.requests.Request)
    request.url = MagicMock()
    request.url.path = "/admin/satellite-orm/edit/123"
    request.method = "GET"
    return request


# tests/conftest.py
@pytest.fixture(scope="session", autouse=True)
async def _apply_migrations_once():
    # Один раз за все тесты — поднимаем БД до актуальной версии через Alembic
    import subprocess, sys, os
    log("Applying Alembic migrations to test DB...")
    env = os.environ.copy()
    env["ENVIRONMENT"] = "unittests"  # или как у тебя называется тестовая env
    subprocess.check_call([sys.executable, "-m", "alembic", "upgrade", "head"], env=env)
    log("Alembic migrations applied.")


#########################################
# grok phantasies...
#########################################


# test_engine = create_async_engine(TEST_DB_URL, echo=True)
@pytest.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    # 1. Тестовый движок (обязательно отдельная БД!)
    # инициализируем окружение единообразно с основным FastAPI-приложением
    # переменные окружения могут прилететь из .env-файла или в контексте запускаемого py.test
    # settings.postgres.DB = os.environ.get("POSTGRES__DB", "soniks_test")
    # assert settings.postgres.DB == "soniks_test"
    # TEST_DB_URL = f"postgresql+asyncpg://{settings.postgres.USER}:{settings.postgres.PASSWORD}@{settings.postgres.HOST}:{settings.postgres.PORT}/soniks_test"
    TEST_DB_URL = settings.postgres.url
    log('init test_engine')
    async_engine = create_async_engine(
        TEST_DB_URL,
        echo=settings.sql_engine.ECHO,
    )
    # return async_engine
    yield async_engine
    log('close test_engine')
    await async_engine.dispose()


@pytest.fixture(scope="session")
async def test_sessionmaker(test_engine):
    sessionmaker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )
    return sessionmaker


@asynccontextmanager
async def savepoint_session(session: AsyncSession):
    await session.execute(sa.text("SAVEPOINT pytest_savepoint"))
    try:
        yield session
    finally:
        await session.execute(sa.text("ROLLBACK TO SAVEPOINT pytest_savepoint"))
        await session.execute(sa.text("RELEASE SAVEPOINT pytest_savepoint"))


# # 2. Одно соединение + все таблицы на всю сессию pytest
# @pytest.fixture(scope="session")
# async def _test_connection_and_models(test_engine):
#     # async with test_engine.begin() as conn:
#     #     await conn.run_sync(BaseORM.metadata.create_all)
#
#     # FIXME: в ближайшей итерации избавляюсь от connect()
#     async with test_engine.connect() as conn:
#         yield conn
#
#     # После всех тестов — чистим
#     # async with test_engine.begin() as conn:
#     #     await conn.run_sync(BaseORM.metadata.drop_all)
#     await test_engine.dispose()
#
#
# # 3. Главная фикстура: сессия с автоматическим rollback после каждого теста
# @pytest.fixture(scope="session")
# async def rolled_back_session(_test_connection_and_models, test_sessionmaker):
#
#     # connection = await _test_connection_and_models()
#     connection = _test_connection_and_models
#
#     async def get_session() -> AsyncGenerator[AsyncSession, None]:
#         # connection = _test_connection_and_models
#         async with test_sessionmaker(bind=connection) as session:
#             async with session.begin():        # ← вот эта магия откатывает ВСЁ
#                 yield session
#             # ← автоматический ROLLBACK, даже если был commit()
#     return get_session

# @pytest.fixture(autouse=True)
@pytest.fixture()
async def rolled_back_session():
    async with async_sessionmaker() as session:
        async with session.begin():
            async with savepoint_session(session):
                yield session


@pytest.fixture(scope="session")
def db_provider(test_engine, test_sessionmaker, rolled_back_session) -> Provider:
    provider = Provider()

    provider.provide(
        lambda: test_engine,
        provides=AsyncEngine,
        scope=Scope.APP,
    )
    provider.provide(
        lambda: test_sessionmaker,
        provides=async_sessionmaker[AsyncSession],
        scope=Scope.APP,
    )
    provider.provide(
        rolled_back_session,
        provides=AsyncSession,
        scope=Scope.REQUEST,
    )
    return provider


# end grok's code
#########################################

# Supply connection string
# engine = create_async_engine("postgresql+psycopg2://...")


# @pytest.fixture(scope="session")
# def dishka_container_factory() -> AsyncContainer:
#     # инициализируем окружение единообразно с основным FastAPI-приложением
#     # переменные окружения могут прилететь из .env-файла или в контексте запускаемого py.test
#     settings.postgres.DB = os.environ.get("POSTGRES__DB", "soniks_test")
#     assert settings.postgres.DB == "soniks_test"
#     dishka_context = {
#         PostgresSettings: settings.postgres,
#         SQLEngineSettings: settings.sql_engine,
#         AuthSettings: settings.auth,
#         AdminSettings: settings.admin,
#         FileSettings: settings.file,
#     }
#     # enter APP scope
#     return make_async_container(*get_providers(), context=dishka_context)


# # норм работал, но не умел чистить транзакцию, grok говорит, нужно хитрее (ниже)
# @pytest.fixture()
# async def dishka_container(dishka_container_factory: AsyncContainer):
#     async with dishka_container_factory() as request_container:
#         yield request_container


#########################################
# grok phantasies...
@pytest.fixture(scope="session")
def dishka_container_factory(
    db_provider: Provider,
    rolled_back_session: AsyncSession,
) -> AsyncContainer:
    # инициализируем окружение единообразно с основным FastAPI-приложением
    # переменные окружения могут прилететь из .env-файла или в контексте запускаемого py.test
    # settings.postgres.DB = os.environ.get("POSTGRES__DB", "soniks_test")
    # assert settings.postgres.DB == "soniks_test"
    dishka_context = {
        PostgresSettings: settings.postgres,
        SQLEngineSettings: settings.sql_engine,
        AuthSettings: settings.auth,
        AdminSettings: settings.admin,
        FileSettings: settings.file,
    }
    # enter APP scope
    providers = get_providers()

    providers = (
        providers[0],
        db_provider,
        *providers[2: ],
    )

    # class TestTransaction:
    #     def __init__(self, session: AsyncSession) -> None:
    #         self._session: AsyncSession = session
    # test_transaction = SQLAlchemyTransaction(rolled_back_session)
    # gateway_provider.provide(test_transaction, provides=Transaction)  # FIXME: нужен тип/класс, не экземпляр
    app_scope_container = make_async_container(*providers, context=dishka_context)

    # FIXME: может быть не хватает setup_dishka() и экземпляра тестового app: FastAPI для него
    return app_scope_container


# 4. Переопределяем твой dishka_container, чтобы он использовал тестовую сессию
@pytest.fixture
async def dishka_container(
    dishka_container_factory: AsyncContainer,
) -> AsyncGenerator[AsyncContainer, None]:
    async with dishka_container_factory() as container:
        yield container

# end grok's code
#########################################


# @pytest.fixture(scope="session")
# async def connection(anyio_backend) -> AsyncGenerator[AsyncConnection, None]:
#     async with engine.connect() as connection:
#         yield connection
#
#
# @pytest.fixture()
# async def transaction(
#     connection: AsyncConnection,
# ) -> AsyncGenerator[AsyncTransaction, None]:
#     async with connection.begin() as transaction:
#         yield transaction


# Use this fixture to get SQLAlchemy's AsyncSession.
# All changes that occur in a test function are rolled back
# after function exits, even if session.commit() is called
# in inner functions
# @pytest.fixture()
# async def session(
#     connection: AsyncConnection, transaction: AsyncTransaction
# ) -> AsyncGenerator[AsyncSession, None]:
#     async_session = AsyncSession(
#         bind=connection,
#         join_transaction_mode="create_savepoint",
#     )
#
#     yield async_session
#
#     await transaction.rollback()

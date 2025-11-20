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
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
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
# 1. Один раз за все тесты применяем миграции (если нужно)
@pytest.fixture(scope="session", autouse=True)
async def _apply_migrations_once():
    import subprocess, sys, os
    log("Applying Alembic migrations to test DB...")
    env = os.environ.copy()
    env["ENVIRONMENT"] = "unittests"  # или как у тебя называется тестовая env
    subprocess.check_call([sys.executable, "-m", "alembic", "upgrade", "head"], env=env)
    log("Alembic migrations applied.")


# 2. Тестовый engine (один на всю сессию, обязательно отдельная БД!)
@pytest.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    log("Creating test AsyncEngine")

    # инициализируем окружение единообразно с основным FastAPI-приложением
    # переменные окружения могут прилететь из .env-файла или в контексте запускаемого py.test
    # settings.postgres.DB = os.environ.get("POSTGRES__DB", "soniks_test")
    # TEST_DB_URL = f"postgresql+asyncpg://{settings.postgres.USER}:{settings.postgres.PASSWORD}@{settings.postgres.HOST}:{settings.postgres.PORT}/soniks_test"
    TEST_DB_URL = settings.postgres.url
    assert TEST_DB_URL.endswith("soniks_test")
    engine = create_async_engine(
        # теоретически, можно воспользоваться и имеющимся в dishka провайдером get_engine
        # больших отличий тут не будет
        # пока оставляю этот только для целостной картины
        # и контролируемой инициализации тестового окружения
        TEST_DB_URL,
        # echo=False,
        echo=settings.sql_engine.ECHO,
    )
    yield engine
    log("Disposing test engine")
    await engine.dispose()


# 3. Тестовый sessionmaker (привязан к test_engine)
@pytest.fixture(scope="session")
def test_sessionmaker(test_engine) -> async_sessionmaker[AsyncSession]:
    log("Creating test sessionmaker")
    # теоретически, можно воспользоваться и имеющимся в dishka провайдером get_session_maker
    # больших отличий тут не будет
    # пока оставляю этот только для целостной картины
    # и контролируемой инициализации тестового окружения
    sessionmaker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )
    return sessionmaker


# 4. SAVEPOINT — магия отката после каждого теста (контекстный менеджер)
@asynccontextmanager
async def _session_with_savepoint(sessionmaker: async_sessionmaker) -> AsyncGenerator[AsyncSession, None]:
    async with sessionmaker() as session:
        async with session.begin():  # внешняя транзакция
            await session.execute(sa.text("SAVEPOINT pytest_sp"))
            try:
                log("SAVEPOINT created — entering test")
                yield session
                # WARN: оригинальный get_session() ловит все SQLAlchemyError
                #       и после роллбэка рейзит ошибку дальше
            finally:
                log("Rolling back to SAVEPOINT")
                await session.execute(sa.text("ROLLBACK TO SAVEPOINT pytest_sp"))
                await session.execute(sa.text("RELEASE SAVEPOINT pytest_sp"))
                await session.rollback()
                log("test session cleaned up")


# 5. Фикстура сессии с откатом (фикстура уровня отдельной тестовой функции, не сессии)
# @pytest.fixture
# async def test_session(test_sessionmaker) -> AsyncGenerator[AsyncSession, None]:
async def get_test_session(sessionmaker: async_sessionmaker[AsyncSession]) -> AsyncGenerator[AsyncSession, None]:
    log("Entering get_test_session()")
    # log("Entering test_session fixture")
    # async with _session_with_savepoint(test_sessionmaker) as session:
    async with _session_with_savepoint(sessionmaker) as session:
        yield session
    # log("Exited test_session fixture — DB clean!")
    log("Exited get_test_session() — DB clean!")


# 6. Провайдер, который подменяет всё нужное в Dishka
# class TestDBProvider(Provider):
#     scope = Scope.APP
#
#     engine = provide(lambda: test_engine, provides=AsyncEngine)
#     sessionmaker = provide(lambda: test_sessionmaker, provides=async_sessionmaker)
#
#     @provide(provides=AsyncSession, scope=Scope.REQUEST)
#     async def get_session(self, test_session: AsyncSession) -> AsyncSession:
#         log("Providing rolled-back AsyncSession to Dishka")
#         return test_session
#
#     @provide(provides=Transaction, scope=Scope.REQUEST)
#     async def get_transaction(self, test_session: AsyncSession) -> Transaction:
#         log("Providing SQLAlchemyTransaction with test session")
#         return SQLAlchemyTransaction(test_session)
#
@pytest.fixture(scope="session")
# def db_provider(test_engine, test_sessionmaker, test_session) -> Provider:
def db_provider(test_engine, test_sessionmaker) -> Provider:
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
        # lambda: test_session,
        get_test_session,
        provides=AsyncSession,
        scope=Scope.REQUEST,
    )
    return provider
#
# @pytest.fixture(scope="session")
# def test_db_provider() -> Generator[TestDBProvider, None, None]:
#     log("Entering test_db_provider fixture (must be used only once...)")
#     yield TestDBProvider()
#     log("Exited test_db_provider fixture (must be used only once...)")


# 7. Переопределяем фабрику контейнера — вставляем наш провайдер вместо продакшеновского
@pytest.fixture(scope="session")
async def dishka_container_factory(
    db_provider: Provider,
    # test_db_provider: TestDBProvider,
) -> AsyncGenerator[AsyncContainer, None]:
    log("Creating Dishka container factory with test DB provider")

    # инициализируем окружение единообразно с основным FastAPI-приложением
    # переменные окружения могут прилететь из .env-файла или в контексте запускаемого py.test
    # settings.postgres.DB = os.environ.get("POSTGRES__DB", "soniks_test")
    assert settings.postgres.DB == "soniks_test"
    dishka_context = {
        PostgresSettings: settings.postgres,
        SQLEngineSettings: settings.sql_engine,
        AuthSettings: settings.auth,
        AdminSettings: settings.admin,
        FileSettings: settings.file,
    }
    original_providers = get_providers()  # твои обычные провайдеры

    # enter APP scope
    # Заменяем инфраструктурный провайдер на наш тестовый
    app_scope_container = make_async_container(
        *original_providers,
        # test_db_provider,  # наш тестовый провайдер просто перезапишет старые
        db_provider,  # наш тестовый провайдер просто перезапишет старые
        context=dishka_context,
    )
    # FIXME: может быть не хватает setup_dishka() и экземпляра тестового app: FastAPI для него
    yield app_scope_container
    log("Exit from dishka_container_factory (must be used only once...)")


# 8. Обычный контейнер — как и раньше, но теперь с откатом!
@pytest.fixture
async def dishka_container(
    dishka_container_factory: AsyncContainer,
) -> AsyncGenerator[AsyncContainer, None]:
    log("Entering request-scoped Dishka container")
    async with dishka_container_factory() as container:
        yield container
    log("Exited request-scoped container")


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

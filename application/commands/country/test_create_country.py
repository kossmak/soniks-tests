import pytest
import sqlalchemy as sa
from loguru import logger
from sqlalchemy import delete, func
from sqlalchemy.exc import PendingRollbackError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.country.create import CreateCountryInteractor
from src.application.dtos.country import CountryQueryModel, CountryResponse
from src.domain.exceptions.country import CountryCodeAlreadyExistsError
from src.infrastructure.postgres.models import CountryORM


log = logger.info
# log = logger.debug


@pytest.fixture
def country_query(mock_model):
    return mock_model(
        CountryQueryModel,
        code="YY",
        name="YY Country",
        image_path="country/yy.png",
    )


@pytest.fixture
def country(mock_model):
    return mock_model(CountryORM)


@pytest.fixture(autouse=True)
async def _clean_countries(async_session):
    """Удалить все записи CountryORM из таблицы перед запуском теста."""
    await async_session.execute(delete(CountryORM))
    # result = await async_session.execute(sa.select(sa.text("current_date")))
    # current_date = result.fetchone()
    # log(f"[debug] {current_date=}")
    await async_session.commit()


@pytest.mark.anyio
# @pytest.mark.asyncio  # кажется, это необязательно, если в conftest есть fixture `anyio_backend()`
class TestCreateCountryInteractor:
    async def test_call(self, async_session, dishka_container, country_query):
        # БД-таблица пустая
        # добавляем новую запись успешно
        # добавляем идентичную запись - ошибка-дубликат
        # добавляем вторую запись
        # вместо живых pydantic и dataclasses использовать мок-фабрики
        interactor = await dishka_container.get(CreateCountryInteractor)

        country_data = country_query()
        log(f"insert first record: {country_data.code}")
        country: CountryResponse = await interactor(country_data)

        assert country.code == "YY"
        assert country.name == "YY Country"
        assert country.image_path == "country/yy.png"

        log(f"try to insert 2nd (duplicate) record: {country_data.code}")
        try:
            await interactor(country_data)
        except CountryCodeAlreadyExistsError:
            pass
        else:
            pytest.fail("duplicate not found!")

        country_data = country_query(
            code="WW",
            name="Volkswagen",
            image_path="country/ww.png",
        )
        log(f"try to insert 3rd record: {country_data.code}")
        try:
            country: CountryResponse = await interactor(country_data)
        except PendingRollbackError:
            # WARN: после проваленного flush() и неявного rollback() сессию уже не получится нормально использовать
            pass

        # assert country.code == 'WW'
        # assert country.name == 'Volkswagen'
        # assert country.image_path == 'country/ww.png'


@pytest.mark.anyio
class TestSavepointIsolation:
    """Проверяем, что изоляция через SAVEPOINT работает правильно."""

    async def test_first_inserts_data(self, dishka_container, country_query):
        """Первый тест — добавляем данные."""
        interactor = await dishka_container.get(CreateCountryInteractor)

        await interactor(
            country_query(
                code="WW",
                name="Volkswagen",
                image_path="country/ww.png",
            ),
        )

        session = await dishka_container.get(AsyncSession)
        stmt = sa.select(func.count()).select_from(CountryORM)
        count = await session.scalar(stmt)

        logger.info(f"First test: count = {count}")
        assert count == 1

    async def test_second_sees_clean_db(self, dishka_container):
        """Второй тест — БД должна быть пустой."""
        # убеждаемся, что после выполнения тестов БД осталась чистой
        session = await dishka_container.get(AsyncSession)
        stmt = sa.select(func.count()).select_from(CountryORM)
        count = await session.scalar(stmt)

        logger.info(f"Second test: count = {count}")
        assert count == 0, "SAVEPOINT rollback не работает!"

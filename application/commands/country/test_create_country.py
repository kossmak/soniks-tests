import pytest
import sqlalchemy as sa
from loguru import logger
from sqlalchemy import delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.country.create import CreateCountryInteractor
from src.application.dtos.country import CountryQueryModel, CountryResponse
from src.domain.exceptions.country import CountryCodeAlreadyExistsError
from src.infrastructure.postgres.models import CountryORM


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


@pytest.fixture(autouse=True)
async def _clean_countries(mock_model, async_session):
    """Удалить все записи CountryORM из таблицы перед запуском теста."""
    await async_session.execute(delete(CountryORM))
    await async_session.commit()


@pytest.mark.anyio
# @pytest.mark.asyncio  # кажется, это необязательно, если в conftest есть fixture `anyio_backend()`
class TestCreateCountryInteractor:


    async def test_call(self, dishka_container, country_query, mocker):
        # БД-таблица пустая
        # добавляем новую запись успешно
        # добавляем идентичную запись - ошибка-дубликат
        # добавляем вторую запись
        # вместо живых pydantic и dataclasses использовать мок-фабрики
        interactor = await dishka_container.get(CreateCountryInteractor)

        country_data = country_query()
        country: CountryResponse = await interactor(country_data)

        assert country.code == 'YY'
        assert country.name == 'YY Country'
        assert country.image_path == 'country/yy.png'

        try:
            await interactor(country_data)
        except CountryCodeAlreadyExistsError:
            pass
        else:
            pytest.fail("duplicate not found!")

        country: CountryResponse = await interactor(
            country_data=country_query(
                code='WW',
                name='Volkswagen',
                image_path='country/ww.png',
            ),
        )

        assert country.code == 'YY'
        assert country.name == 'YY Country'
        assert country.image_path == 'country/yy.png'

@pytest.mark.anyio
class TestSavepointIsolation:
    """Проверяем, что изоляция через SAVEPOINT работает правильно."""

    async def test_first_inserts_data(self, dishka_container, country_query):
        """Первый тест — добавляем данные."""
        interactor = await dishka_container.get(CreateCountryInteractor)

        await interactor(country_query(code='WW', name='Volkswagen', image_path='country/ww.png'))

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

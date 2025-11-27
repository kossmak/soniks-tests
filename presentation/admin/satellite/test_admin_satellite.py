
import sqlalchemy as sa
import pytest
from loguru import logger
from starlette.testclient import TestClient

from src.infrastructure.postgres.models import CountryORM, DecoderORM, OperatorORM, SatelliteProjectORM
from src.infrastructure.postgres.models import SatelliteORM
from src.infrastructure.postgres.models import TransmitterORM
from src.presentation.admin import SatelliteAdmin


@pytest.fixture
def satellite(mock_model) -> None:
    return mock_model(SatelliteORM)


@pytest.fixture(autouse=True)
async def _init_fk(async_session) -> None:
    """Удалить все ненужные записи из справочников и создать необходимые."""
    await async_session.execute(sa.delete(CountryORM))
    async_session.add(CountryORM(
        code="ru",
        name="Russia",
        image_path="country/ru.png",
    ))
    await async_session.execute(sa.delete(DecoderORM))
    async_session.add(DecoderORM(
        name="FMDecoder",
    ))
    await async_session.execute(sa.delete(OperatorORM))
    async_session.add(OperatorORM(
        name="FirstOperator",
    ))
    await async_session.execute(sa.delete(SatelliteProjectORM))
    async_session.add(SatelliteProjectORM(
        name="NewProject",
    ))
    await async_session.commit()


@pytest.fixture(autouse=True)
async def _clean_satellites(async_session) -> None:
    """Удалить все записи SatelliteORM."""
    await async_session.execute(sa.delete(SatelliteORM))  # TransmitterORM удаляются каскадно
    await async_session.commit()


@pytest.fixture(autouse=True)
def _add_admin(admin) -> None:
    logger.info("adding SatelliteAdmin view into application")
    admin.add_view(SatelliteAdmin)


@pytest.mark.anyio
class TestSatelliteAdmin:

    async def test_root_view(self, client) -> None:
        response = await client.get("/admin", timeout=1)

        assert response.status_code == 200
        assert '<span class="nav-link-title">Satellites</span>' in response.text

    # async def test_create_satellite(self, dishka_container):
    #     ...

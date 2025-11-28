from typing import Any
from unittest.mock import Mock

import sqlalchemy as sa
import pytest
from loguru import logger
from starlette.datastructures import ImmutableMultiDict, URL
from starlette.requests import Request
from starlette.testclient import TestClient

from src.domain.entities.satellite import SatelliteStatusEnum, TransmitterStatusEnum, TransmitterTypeEnum
from src.infrastructure.postgres.models import CountryORM, DecoderORM, OperatorORM, SatelliteProjectORM
from src.infrastructure.postgres.models import SatelliteORM
from src.infrastructure.postgres.models import TransmitterORM
from src.presentation.admin import SatelliteAdmin


# @pytest.fixture
# def satellite(mock_model) -> None:
#     return mock_model(SatelliteORM)


@pytest.fixture
def satellite_form_data():
    """Базовые данные формы для создания спутника."""
    return {
        "call_sign": "TEST-SAT",
        "name": "Test Satellite",
        "norad_id": "99999",
        "sat_id": "TEST-001",
        "status": SatelliteStatusEnum.ON_ORBIT.name,
        "description": "Test satellite description",
        "launch_date": "2024-01-15 12:00:00",
        # FK references (передаются как строковые ID)
        "countries": ["RU"],  # ID страны Russia
        "decoder": "1",
        "operator": "1",
        "project": "1",
        "launch": "",  # необязательное поле
        "deployer_uuid": "",
        "image_file": "",  # файл не загружаем в базовых тестах
    }


@pytest.fixture
def transmitter_form_data():
    """Базовые данные для одного трансмиттера."""
    return {
        "satnogs_uuid": "test-uuid-001",
        "description": "Test transmitter",
        "citation": "https://example.com/citation",
        "downlink_frequency": "145000000",
        "uplink_frequency": "",
        "downlink_drift": "",
        "uplink_drift": "",
        "downlink_mode": "FM",
        "uplink_mode": "",
        "type": TransmitterTypeEnum.TRANSMITTER.name,
        "status": TransmitterStatusEnum.ACTIVE.name,
        "baud": "9600",
    }



@pytest.fixture(autouse=True)
async def _init_fk(async_session) -> None:
    """Удалить все ненужные записи из справочников и создать необходимые."""
    await async_session.execute(sa.delete(CountryORM))
    async_session.add(CountryORM(
        code="RU",
        name="Russia",
        image_path="country/ru.png",
    ))
    await async_session.execute(sa.delete(DecoderORM))
    async_session.add(DecoderORM(
        id=1,
        name="FMDecoder",
    ))
    await async_session.execute(sa.delete(OperatorORM))
    async_session.add(OperatorORM(
        id=1,
        name="FirstOperator",
    ))
    await async_session.execute(sa.delete(SatelliteProjectORM))
    async_session.add(SatelliteProjectORM(
        id=1,
        name="NewProject",
    ))
    await async_session.commit()


@pytest.fixture(autouse=True)
async def _clean_satellites(async_session) -> None:
    """Удалить все записи SatelliteORM."""
    await async_session.execute(sa.delete(SatelliteORM))  # TransmitterORM удаляются каскадно
    await async_session.commit()


# @pytest.fixture(autouse=True)
# def _add_admin(admin) -> None:
#     logger.info("adding SatelliteAdmin view into application")
#     admin.add_view(SatelliteAdmin)
@pytest.fixture
def satellite_admin(admin):
    """Экземпляр SatelliteAdmin."""
    admin.add_view(SatelliteAdmin)
    # Получаем зарегистрированный view
    return admin._views[-1]


def make_form_data(
    base_data: dict[str, Any],
    transmitters: list[dict[str, Any]] | None = None,
) -> ImmutableMultiDict:
    """
    Создаёт ImmutableMultiDict для имитации данных формы с вложенными трансмиттерами.

    SQLAdmin + WTForms ожидают данные в формате:
    {
        "field": "value",
        "transmitters-0-field": "value",
        "transmitters-1-field": "value",
    }
    """
    form_data = dict(base_data)

    if transmitters:
        for idx, transmitter in enumerate(transmitters):
            for key, value in transmitter.items():
                form_data[f"transmitters-{idx}-{key}"] = value

    return ImmutableMultiDict(form_data)  # type: ignore


@pytest.mark.anyio
class TestSatelliteAdminList:

    async def test_root_view(self, client) -> None:
        response = await client.get("/admin", timeout=1)

        assert response.status_code == 200
        assert '<span class="nav-link-title">Satellites</span>' in response.text

    # async def test_create_satellite(self, dishka_container):
    #     ...

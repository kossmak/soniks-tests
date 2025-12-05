from typing import Any

import pytest
import sqlalchemy as sa
from starlette.datastructures import ImmutableMultiDict

from src.domain.entities.satellite import (
    SatelliteStatusEnum,
    TransmitterStatusEnum,
    TransmitterTypeEnum,
)
from src.infrastructure.postgres.models import (
    CountryORM,
    DecoderORM,
    OperatorORM,
    SatelliteORM,
    SatelliteProjectORM,
)
from src.presentation.admin import SatelliteAdmin
from tests._utils import parse_html


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
        # FK references (прилетают из админки как строковые ID)
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
    async_session.add(
        CountryORM(
            code="RU",
            name="Russia",
            image_path="country/ru.png",
        )
    )
    await async_session.execute(sa.delete(DecoderORM))
    async_session.add(
        DecoderORM(
            id=1,
            name="FMDecoder",
        )
    )
    await async_session.execute(sa.delete(OperatorORM))
    async_session.add(
        OperatorORM(
            id=1,
            name="FirstOperator",
        )
    )
    await async_session.execute(sa.delete(SatelliteProjectORM))
    async_session.add(
        SatelliteProjectORM(
            id=1,
            name="NewProject",
        )
    )
    await async_session.commit()


@pytest.fixture(autouse=True)
async def _clean_satellites(async_session) -> None:
    """Удалить все записи SatelliteORM."""
    await async_session.execute(
        sa.delete(SatelliteORM)
    )  # TransmitterORM удаляются каскадно
    await async_session.commit()


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
    async def test_empty_list(
        self, admin, satellite_admin, mock_request, mock_admin_url
    ):
        """Пустой список спутников."""
        request = mock_request(
            url=mock_admin_url("/admin/satellite-orm/list"),
            path_params={"identity": "satellite-orm"},
        )
        response = await admin.list(request)

        assert response.status_code == 200

        # BaseAdmin возвращает TemplateResponse
        assert (
            response.template.name == "sqladmin/list.html"
        )  # используем дефолтный шаблон из пакета

        soup = parse_html(body=response.body)

        search_input = soup.find("input", {"id": "search-input"})
        assert (
            search_input.get("placeholder")
            == "Search: uuid, sat_id, call_sign, norad_id, name"
        )

        filters = (
            soup.find(
                "div",
                {"id": "filter-sidebar"},
            )
            .find_next(
                "div",
                {"class": "list-group-item"},
            )
            .find_all_next("a")
        )

        assert [f.text.strip() for f in filters] == ["All"] + [
            str(s) for s in SatelliteStatusEnum
        ]

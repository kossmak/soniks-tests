import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.satellite.add_from_satnogs import (
    AddNewSatellitesInteractor,
)
from src.application.dtos.satellite import (
    SatelliteSatnogsRequest,
    TransmitterSatnogsRequest,
)
from src.domain.exceptions.satellite.business_rules import (
    SatelliteSatIDAlreadyExistsError,
)


def test_httpx_experiment():
    pass


# @pytest.mark.asyncio  # claude's variant
@pytest.mark.skip
@pytest.mark.anyio
class TestCreateSatelliteInteractor:
    async def test_call(self, dishka_container, mocker):
        # FIXME: инициализировать fixtur'ы:
        # БД-таблица пустая
        # добавляем новую запись успешно
        # добавляем идентичную запись - ошибка-дубликат
        # добавляем вторую запись
        # убеждаемся, что после выполнения тестов БД осталась чистой
        # вместо живых pydantic и dataclasses использовать мок-фабрики

        interactor = await dishka_container.get(AddNewSatellitesInteractor)

        satellite_data = SatelliteSatnogsRequest(
            sat_id="SCHX-0895-2361-9925-0310",
            norad_id=999987,
            name="YY Tst Satellite",
            status="alive",  # see SatelliteMapper.satellite_status_mapper
            countries="YY",
            decoder=None,
            operator=None,
            transmitters=[
                TransmitterSatnogsRequest(
                    satnogs_uuid="Bfcf32GD9uohSXHMoT2Mw9",
                    description="400Mhz beacon TEST",
                    citation="Change frequency to expected one and the drifted",
                    downlink_mode="FM",
                    uplink_mode=None,
                    downlink_low=400000000,
                    downlink_high=400000000,
                    uplink_low=None,
                    uplink_high=None,
                    downlink_drift=None,
                    uplink_drift=None,
                    baud=0,
                    status="active",
                    type="Transmitter",
                ),
            ],
        )

        # похоже не работает - вставка записей коммитится, несмотря на патч
        mock_commit = mocker.patch.object(
            interactor._transaction, "commit", return_value=None, autospec=True
        )

        satellite = await interactor([satellite_data])

        interactor._transaction.rollback()

        assert satellite.code == "YY"
        assert satellite.name == "YY Satellite"
        assert satellite.image_path == "satellite/yy.png"

        assert mock_commit.call_count == 1

        try:
            await interactor(satellite_data)
        except SatelliteSatIDAlreadyExistsError:
            pass
        else:
            assert False, "duplicate not found!"

        # FIXME: [test] сессия уже есть в интеракторе, нужно только её пропатчить, чтобы rollback'алась
        session = await dishka_container.get(AsyncSession)
        # session.execute(sa.text("delete from satellite where code = :code"), code='YY')
        session.delete(satellite)
        session.commit()

        # и второй раз попробовать:
        # assert mock_commit.call_count == 1
        satellite = await interactor(satellite_data)

        interactor._transaction.rollback()

        assert satellite.code == "YY"
        assert satellite.name == "YY Satellite"
        assert satellite.image_path == "satellite/yy.png"

        assert mock_commit.call_count == 2
        session.delete(satellite)
        session.commit()

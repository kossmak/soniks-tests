from unittest.mock import Mock

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.satellite.create_or_update import CreateOrUpdateSatelliteInteractor
from src.application.dtos.satellite import SatelliteQueryRequest
from src.domain.exceptions.satellite.business_rules import SatelliteSatIDAlreadyExistsError

def test_httpx_experiment():
    import httpx
    import asyncio


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

        interactor = await dishka_container.get(CreateOrUpdateSatelliteInteractor)

        satellite_data = SatelliteQueryRequest(
            code='YY',
            name='YY Satellite',
            image_path="satellite/yy.png",
        )


        # похоже не работает - вставка записей коммитится, несмотря на патч
        mock_commit = mocker.patch.object(interactor._transaction, 'commit', return_value=None, autospec=True)

        satellite = await interactor(satellite_data)

        interactor._transaction.rollback()

        assert satellite.code == 'YY'
        assert satellite.name == 'YY Satellite'
        assert satellite.image_path == 'satellite/yy.png'

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

        assert satellite.code == 'YY'
        assert satellite.name == 'YY Satellite'
        assert satellite.image_path == 'satellite/yy.png'

        assert mock_commit.call_count == 2
        session.delete(satellite)
        session.commit()

import datetime
import uuid
from typing import Any, Callable

import pydantic
import pytest
from pytest import fixture

from src.application.dtos.satellite import CreateSatelliteRequest
from src.domain.entities.satellite import SatelliteStatusEnum, TransmitterStatusEnum, TransmitterTypeEnum


@pytest.mark.anyio
class TestCreateSatelliteRequest:

    @fixture
    def transmitter(self) -> Callable[..., Any]:
        def factory(**kwargs) -> dict[str, Any]:
            prototype = {
                # "uuid": "878379a2-eae3-42d9-8ce3-55031a363920",
                "satnogs_uuid": "UzPz4gcsNBPKPKAFPmer7g",
                "description": "Upper side band (drifting)",
                "citation": "https://secwww.jhuapl.edu/techdigest/Content/techdigest/pdf/V05-N04/05-04-Danchik.pdf",
                "downlink_mode": "USB",
                "uplink_mode": None,
                "downlink_frequency": 136658500,
                "uplink_frequency": None,
                "downlink_drift": None,
                "uplink_drift": None,
                "baud": 120224,
                "status": TransmitterStatusEnum.ACTIVE,
                "type": TransmitterTypeEnum.TRANSMITTER,
            }
            return {**prototype, **kwargs}
        return factory

    @fixture
    def satellite(self, transmitter) -> Callable[..., Any]:
        def factory(**kwargs) -> dict[str, Any]:
            prototype = {
                "call_sign": "CATHEDRALE",
                "countries": {"RU", "US"},
                "decoder": "16",
                "deployer_uuid": None,
                "description": "ook! third manually аддед",
                "image_path": None,
                "launch": "0503479c-f2ba-4e78-8182-3b8be9ab2fec",
                "launch_date": datetime.datetime(2022, 10, 10, 12, 0),
                "name": "TyanGuan",
                "norad_id": 5111523,
                "operator": None,
                "project": None,
                "sat_id": "",
                "status": SatelliteStatusEnum.PLANNED,
                "transmitters": [
                    transmitter(),
                ],
            }
            return {**prototype, **kwargs}
        return factory

    async def test_empty_satellite(self, satellite, transmitter):
        raw_data = satellite(
            call_sign="",
            countries="",
            decoder="",
            deployer_uuid="",
            description="",
            image_path="",
            launch="",
            launch_date="",
            name="",
            norad_id="",
            operator="",
            project="",
            sat_id="",
        )
        with pytest.raises(pydantic.ValidationError) as err:
            CreateSatelliteRequest.model_validate(raw_data)

        assert err.value.title == "CreateSatelliteRequest"
        errors = err.value.errors()
        locs = {err["loc"] for err in errors}
        assert locs == {
            ("name",),
        }
        # assert err.value.errors() == [
        #     {
        #         'type': 'string_type',
        #         'loc': ('name',),
        #         'msg': 'Input should be a valid string',
        #         'input': None,
        #         'url': 'https://errors.pydantic.dev/2.11/v/string_type'
        #     },
        #     {
        #         'type': 'set_type',
        #         'loc': ('countries',),
        #         'msg': 'Input should be a valid set',
        #         'input': None,
        #         'url': 'https://errors.pydantic.dev/2.11/v/set_type'
        #     },
        # ]

        # корректные None вместо ""
        raw_data.update({
            "name": "Sputnik-1",
        })
        data = CreateSatelliteRequest.model_validate(raw_data)
        assert data.call_sign is None
        assert data.countries == set()
        assert data.decoder_id is None
        assert data.deployer_uuid is None
        assert data.description is None
        assert data.launch_uuid is None
        assert data.launch_date is None
        assert data.name == "Sputnik-1"
        assert data.norad_id is None
        assert data.operator_id is None
        assert data.project_id is None
        assert data.sat_id is None
        assert data.status == SatelliteStatusEnum.PLANNED

        assert len(data.transmitters) == 1

        # пустой трансмиттер
        raw_data.update({
            "transmitters": [
                transmitter(
                    # пустые строки нужно транслировать в None,
                    # чтобы, например, не спотыкался constraint uq_transmitters_satnogs_uuid
                    description="",
                    satnogs_uuid="",
                    downlink_mode="",
                    uplink_mode="",
                    downlink_frequency="",
                    downlink_drift="",
                    uplink_drift="",
                    baud="",
                    status="",
                    type="",
                ),
            ],
        })
        with pytest.raises(pydantic.ValidationError) as err:
            CreateSatelliteRequest.model_validate(raw_data)

        assert err.value.title == "CreateSatelliteRequest"
        errors = err.value.errors()
        locs = {err["loc"] for err in errors}
        assert locs == {
            ("transmitters", 0, "description"),
            ("transmitters", 0, "status"),
            ("transmitters", 0, "type"),
        }

        raw_data["transmitters"][0].update({
            "description": "Upper side band (drifting)",
            "status": TransmitterStatusEnum.ACTIVE,
            "type": TransmitterTypeEnum.TRANSMITTER,
        })
        data = CreateSatelliteRequest.model_validate(raw_data)
        t1 = data.transmitters[0]
        assert t1.model_dump() == {
            "satnogs_uuid": None,
            "description": "Upper side band (drifting)",
            "citation": "https://secwww.jhuapl.edu/techdigest/Content/techdigest/pdf/V05-N04/05-04-Danchik.pdf",
            "downlink_mode": None,
            "uplink_mode": None,
            "downlink_frequency": None,
            "uplink_frequency": None,
            "downlink_drift": None,
            "uplink_drift": None,
            "baud": None,
            "status": TransmitterStatusEnum.ACTIVE,
            "type": TransmitterTypeEnum.TRANSMITTER,
        }

    async def test_model_validate(self, satellite, transmitter):
        raw_data = satellite(
            transmitters=[
                transmitter(),
                transmitter(
                    # пустые строки нужно транслировать в None,
                    # чтобы, например, не спотыкался constraint uq_transmitters_satnogs_uuid
                    satnogs_uuid="",
                    downlink_mode="",
                    uplink_mode="",
                    downlink_frequency="",
                    downlink_drift="",
                    uplink_drift="",
                    baud="",
                    status="неактивный",
                    type="передатчик",
                ),
                transmitter(
                    satnogs_uuid="xVNv3Gze2CGndzY9FxTixE",
                    description="TLM",
                    citation="https://www.satellitenwelt.de/transit_5b-5.htm",
                    downlink_mode="FMN",
                    uplink_mode=None,
                    downlink_frequency=136650000,
                    uplink_frequency=None,
                    downlink_drift=21954,
                    uplink_drift=None,
                    baud=3451431,
                    status=TransmitterStatusEnum.ACTIVE,
                    type=TransmitterTypeEnum.TRANSCEIVER,
                ),
            ],
        )

        # рекомендуемый PyDV2 вариант валидации/инстанцирования - через .model_validate()
        #   - умеет и словари, и модели проглатывать, и отдельные атрибуты
        data = CreateSatelliteRequest.model_validate(raw_data)
        assert data.call_sign == "CATHEDRALE"
        assert data.countries == {"RU", "US"}
        assert data.decoder_id == 16
        assert data.deployer_uuid is None
        assert data.description == "ook! third manually аддед"
        assert data.launch_uuid.hex == uuid.UUID("0503479c-f2ba-4e78-8182-3b8be9ab2fec").hex
        assert data.launch_date == datetime.datetime(2022, 10, 10, 12, 0)
        assert data.name == "TyanGuan"
        assert data.norad_id == 5111523
        assert data.operator_id is None
        assert data.project_id is None
        assert data.sat_id is None
        assert data.status == SatelliteStatusEnum.PLANNED
        t1, t2, t3 = data.transmitters
        assert t1.model_dump() == {
            # "uuid": "878379a2-eae3-42d9-8ce3-55031a363920",
            "satnogs_uuid": "UzPz4gcsNBPKPKAFPmer7g",
            "description": "Upper side band (drifting)",
            "citation": "https://secwww.jhuapl.edu/techdigest/Content/techdigest/pdf/V05-N04/05-04-Danchik.pdf",
            "downlink_mode": "USB",
            "uplink_mode": None,
            "downlink_frequency": 136658500,
            "uplink_frequency": None,
            "downlink_drift": None,
            "uplink_drift": None,
            "baud": 120224,
            "status": TransmitterStatusEnum.ACTIVE,
            "type": TransmitterTypeEnum.TRANSMITTER,
        }
        assert t2.model_dump() == {
            "satnogs_uuid": None,
            "downlink_mode": None,
            "uplink_mode": None, 
            "downlink_frequency": None,
            "uplink_frequency": None,
            "downlink_drift": None,
            "uplink_drift": None, 
            "baud": None,  # FIXME: в TransmitterORM.baud - обязательное поле
            "description": "Upper side band (drifting)",
            "citation": "https://secwww.jhuapl.edu/techdigest/Content/techdigest/pdf/V05-N04/05-04-Danchik.pdf",
            "status": TransmitterStatusEnum.INACTIVE,
            "type": TransmitterTypeEnum.TRANSMITTER,
        }
        assert t3.model_dump() == {
            "satnogs_uuid": "xVNv3Gze2CGndzY9FxTixE",
            "description": "TLM",
            "citation": "https://www.satellitenwelt.de/transit_5b-5.htm",
            "downlink_mode": "FMN",
            "uplink_mode": None,
            "downlink_frequency": 136650000,
            "uplink_frequency": None,
            "downlink_drift": 21954,
            "uplink_drift": None,
            "baud": 3451431,
            "status": TransmitterStatusEnum.ACTIVE,
            "type": TransmitterTypeEnum.TRANSCEIVER,
        }

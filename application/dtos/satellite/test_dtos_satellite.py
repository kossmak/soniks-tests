import datetime
import uuid

from src.application.dtos.satellite import CreateSatelliteRequest
from src.domain.entities.satellite import SatelliteStatusEnum, TransmitterStatusEnum, TransmitterTypeEnum


class TestCreateSatelliteRequest:

    def test_model_validate(self):
        raw_data = {
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
                {
                    # "uuid": "878379a2-eae3-42d9-8ce3-55031a363920",
                    "satnogs_uuid": "UzPz4gcsNBPKPKAFPmer7g",
                    "description": "Upper side band (drifting)",
                    "citation": "https://secwww.jhuapl.edu/techdigest/Content/techdigest/pdf/V05-N04/05-04-Danchik.pdf https://www.satellitenwelt.de/transit_5b-5.htm",
                    "downlink_mode": "USB",
                    "uplink_mode": None,
                    "downlink_frequency": 136658500,
                    "uplink_frequency": None,
                    "downlink_drift": None,
                    "uplink_drift": None,
                    "baud": 120224,
                    "status": TransmitterStatusEnum.ACTIVE,
                    "type": TransmitterTypeEnum.TRANSMITTER,
                },
                {
                    # "uuid": "214fb94f-a493-426b-8b2a-60941ab06352",
                    "satnogs_uuid": "xVNv3Gze2CGndzY9FxTixE",
                    "description": "TLM",
                    "citation": "https://secwww.jhuapl.edu/techdigest/Content/techdigest/pdf/V05-N04/05-04-Danchik.pdf https://www.satellitenwelt.de/transit_5b-5.htm",
                    "downlink_mode": "FMN",
                    "uplink_mode": None,
                    "downlink_frequency": 136650000,
                    "uplink_frequency": None,
                    "downlink_drift": 21954,
                    "uplink_drift": None,
                    "baud": 3451431,
                    "status": TransmitterStatusEnum.ACTIVE,
                    "type": TransmitterTypeEnum.TRANSCEIVER,
                },
            ],
        }

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
        assert data.sat_id is ''
        assert data.status == SatelliteStatusEnum.PLANNED
        t1, t2 = data.transmitters
        assert t1.model_dump() == {
            # "uuid": "878379a2-eae3-42d9-8ce3-55031a363920",
            "satnogs_uuid": "UzPz4gcsNBPKPKAFPmer7g",
            "description": "Upper side band (drifting)",
            "citation": "https://secwww.jhuapl.edu/techdigest/Content/techdigest/pdf/V05-N04/05-04-Danchik.pdf https://www.satellitenwelt.de/transit_5b-5.htm",
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

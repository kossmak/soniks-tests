from unittest.mock import MagicMock

import pytest
from src.application.dtos.country import CountryQueryModel
from src.infrastructure.postgres.models import CountryORM


@pytest.fixture
def country_query(mock_model):
    return mock_model(
        CountryQueryModel,
        code='YY',  # дефолтные параметры
        name='YY Country',
        image_path="country/yy.png",
    )


@pytest.fixture
def country(mock_model):
    return mock_model(CountryORM)


@pytest.mark.anyio
# @pytest.mark.asyncio
class TestMockModels:
    async def test_models(self, country_query):
        c1 = country_query()
        c2 = country_query(
            code='YY',  # переопределяем дефолтные параметры
            name='YY Country',
            image_path="country/yy.png",
        )
        assert c1.code == c2.code
        assert c1.name == c2.name
        assert c1.image_path == c2.image_path

        assert c2.code == 'YY'
        assert c2.name == 'YY Country'
        assert c2.image_path == "country/yy.png"

        c3 = country_query(name='AB')  # другое значение для одного из полей
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

        # Первое обращение — unittest.mock автоматически создаст MagicMock
        lazy_value = c1.image_path
        assert c1.image_path != 'country/yy.png'  # дефолт не был задан
        assert isinstance(lazy_value, MagicMock)
        assert isinstance(c1.image_path, MagicMock)

        assert str(lazy_value).startswith("<MagicMock name='mock.image_path'")


def test_regex():
    import re
    pattern = re.compile("^[A-Z]{2}$")

    assert re.match(pattern,"ZZ")
    assert re.match(pattern,"ZZasd") is None
    assert re.match(pattern,"11") is None

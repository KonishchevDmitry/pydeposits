import datetime
import os

import pytest

from pydeposits import sbrf

DATA_PATH = os.path.dirname(__file__)

TEST_RATES = [{
    "class": sbrf._CurrencyRates,
    "date": datetime.date(2016, 1, 4),
    "xls": "sberbank_currencies.xls",
    "rates": {
        "USD_SBRF": (76.05, 70.25),
        "EUR_SBRF": (82.65, 76.55),
    }
}, {
    "class": sbrf._MetalRates,
    "date": datetime.date(2016, 2, 20),
    "xls": "sberbank_metals.xls",
    "rates": {
        "AUR_SBRF": (3313, 2757),
        "AGR_SBRF": (41.550000000000004, 34.449999999999996),
        "PTR_SBRF": (2542, 2094),
        "PDR_SBRF": (1375, 1091),
    }
}]


@pytest.mark.parametrize("data", TEST_RATES)
def test_parsing(data):
    with open(os.path.join(DATA_PATH, data["xls"]), "rb") as xls:
        assert data["class"]().parse(xls.read()) == data["rates"]


@pytest.mark.parametrize("data", TEST_RATES)
def test_receiving(data):
    assert data["class"]().get_for_date(data["date"]) == data["rates"]


@pytest.mark.slow
@pytest.mark.parametrize("data", TEST_RATES)
def test_receiving_all_history(data):
    total_days, no_data_days = 0, 0

    rates = data["class"]()
    date = rates._min_supported_date
    today = datetime.date.today()

    while date <= today:
        total_days += 1
        if not rates.get_for_date(date):
            no_data_days += 1

        date += datetime.timedelta(days=1)

    assert no_data_days < total_days / 2

import logging

import pytest

import pcli.log


@pytest.fixture(autouse=True, scope="session")
def test():
    pcli.log.setup(debug_mode=True, level=logging.WARN)

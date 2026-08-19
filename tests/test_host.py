import os

import pytest

from pyclidata.host import get_host, set_host

ENV_KEYS = ["CLIDATA_HOST", "CLIDATA_PORT", "CLIDATA_SERVICE"]


@pytest.fixture(autouse=True)
def _clean_env():
    saved = {k: os.environ.pop(k, None) for k in ENV_KEYS}
    yield
    for k in ENV_KEYS:
        os.environ.pop(k, None)
        if saved[k] is not None:
            os.environ[k] = saved[k]


def test_get_host_returns_sensible_defaults():
    h = get_host()
    assert h["host"] == "clidatadb1"
    assert h["port"] == "1521"
    assert h["service"] == "CLIDATA"


def test_set_host_overrides_defaults_for_the_session():
    # persist=False: session-only, so the test never touches the real
    # persisted config file
    set_host(host="10.0.0.5", port="1522", service="CLIDATA_TEST", persist=False)
    h = get_host()

    assert h["host"] == "10.0.0.5"
    assert h["port"] == "1522"
    assert h["service"] == "CLIDATA_TEST"

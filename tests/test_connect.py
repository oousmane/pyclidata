import oracledb
import pytest

from pyclidata import connect


class _FakeErrorInfo:
    def __init__(self, full_code: str, message: str = "boom"):
        self.full_code = full_code
        self.message = message

    def __str__(self):
        return f"{self.full_code}: {self.message}"


@pytest.fixture(autouse=True)
def _patch_creds_and_host(monkeypatch):
    monkeypatch.setattr(
        connect, "get_user_creds", lambda user=None: {"user": "ousmane", "password": "x"}
    )
    monkeypatch.setattr(
        connect,
        "get_host",
        lambda: {"host": "192.168.1.129", "port": "1521", "service": "CLIDATA"},
    )


def test_dpy_3015_in_thin_mode_gets_instant_client_hint(monkeypatch):
    def _raise_connect(**kwargs):
        raise oracledb.NotSupportedError(_FakeErrorInfo("DPY-3015"))

    monkeypatch.setattr(oracledb, "connect", _raise_connect)
    monkeypatch.setattr(oracledb, "is_thin_mode", lambda: True)

    with pytest.raises(ConnectionError) as exc_info:
        connect.open_clidatadb()

    assert "Connection error: DPY-3015" in str(exc_info.value)
    assert "DPY-3015" in str(exc_info.value)


def test_other_errors_get_no_hint(monkeypatch):
    def _raise_connect(**kwargs):
        raise oracledb.DatabaseError(_FakeErrorInfo("DPY-4011", "bad password"))

    monkeypatch.setattr(oracledb, "connect", _raise_connect)
    monkeypatch.setattr(oracledb, "is_thin_mode", lambda: True)

    with pytest.raises(ConnectionError) as exc_info:
        connect.open_clidatadb()

    assert "Connection error: DPY-3015" not in str(exc_info.value)
    assert "DPY-4011" in str(exc_info.value)


def test_dpy_3015_in_thick_mode_gets_no_hint(monkeypatch):
    # If we're already in thick mode, DPY-3015 means something else is
    # wrong -- an Instant Client version/config issue, not "none found" --
    # so the "go install one" hint would be misleading.
    def _raise_connect(**kwargs):
        raise oracledb.NotSupportedError(_FakeErrorInfo("DPY-3015"))

    monkeypatch.setattr(oracledb, "connect", _raise_connect)
    monkeypatch.setattr(oracledb, "is_thin_mode", lambda: False)

    with pytest.raises(ConnectionError) as exc_info:
        connect.open_clidatadb()

    assert "Connection error: DPY-3015" not in str(exc_info.value)

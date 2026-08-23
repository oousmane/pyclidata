import ibis
import oracledb
import pytest

from pyclidata import checks


class _FakeConnection(oracledb.Connection):
    def __init__(self):
        pass


@pytest.fixture
def fake_table():
    return ibis.memtable({"a": [1, 2, 3]})


def test_is_connection(fake_table):
    assert checks.is_connection(_FakeConnection())
    assert not checks.is_connection(fake_table)
    assert not checks.is_connection("not a connection")


def test_is_lazy_table(fake_table):
    assert checks.is_lazy_table(fake_table)
    assert not checks.is_lazy_table(_FakeConnection())
    assert not checks.is_lazy_table("not a table")


def test_check_connection_passes_through(fake_table):
    con = _FakeConnection()
    assert checks.check_connection(con) is con


def test_check_connection_raises_with_arg_name_in_message(fake_table):
    with pytest.raises(TypeError, match="`con` must be an open connection"):
        checks.check_connection(fake_table, arg="con")


def test_check_table_passes_through(fake_table):
    assert checks.check_table(fake_table) is fake_table


def test_check_table_raises_with_arg_name_in_message():
    with pytest.raises(TypeError, match="`v_day` must be a remote table"):
        checks.check_table(_FakeConnection(), arg="v_day")

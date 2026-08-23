import ibis
import pytest

from pyclidata import tables


def test_list_tables_rejects_invalid_connection():
    with pytest.raises(TypeError, match="must be an open connection"):
        tables.list_tables(con="not a connection")


def test_list_views_rejects_invalid_connection():
    with pytest.raises(TypeError, match="must be an open connection"):
        tables.list_views(con="not a connection")


def test_get_table_rejects_invalid_connection():
    with pytest.raises(TypeError, match="must be an open connection"):
        tables.get_table("V_DAY_ALL_NULL", con="not a connection")


def test_list_variables_rejects_invalid_connection_for_string_table():
    with pytest.raises(TypeError, match="must be an open connection"):
        tables.list_variables("V_DAY_ALL_NULL", con="not a connection")


def test_list_variables_rejects_invalid_table_type():
    with pytest.raises(TypeError, match="must be a remote table"):
        tables.list_variables(42)


def test_list_variables_accepts_a_get_table_style_result():
    fake_table = ibis.memtable({"year": [2024], "value": [1.0]})
    assert tables.list_variables(fake_table) == ["year", "value"]

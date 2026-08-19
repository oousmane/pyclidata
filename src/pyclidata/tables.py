"""Discover and fetch CLIDATA/Oracle tables and views.

get_table() always returns a lazy table -- nothing runs until you
filter/collect it, mirroring the R package's dbplyr-based default. It
uses Ibis to translate table expressions to SQL, pushing filters/selects
down instead of pulling a whole table into memory first: important for
tables too large to load in full (CLIDATA's own V_DAY_ALL_NULL, for
instance, is 1.5+ billion rows). Chain `.filter()`/`.select()`/
`.limit()` then call `.to_pandas()`/`.execute()` to actually run it.

Ibis manages its own connection lifecycle (needed to compile/run SQL
lazily), separate from the raw oracledb.Connection used elsewhere in
this module for list_tables()/list_views()/list_variables() -- so this
opens a second physical connection alongside an existing `con`, reusing
the same target/credentials. It's cached per `con` (via a
WeakKeyDictionary, so it's cleaned up once `con` itself is
garbage-collected) so repeated get_table() calls on the same connection
don't reopen it each time.
"""

from __future__ import annotations

import weakref
from typing import Any

import ibis
import ibis.expr.operations as ops
import oracledb
import pandas as pd
from ibis.backends.oracle import metadata_row_to_type

_ibis_cache: "weakref.WeakKeyDictionary[oracledb.Connection, ibis.BaseBackend]" = (
    weakref.WeakKeyDictionary()
)


def _check_con(con: Any) -> None:
    if con is None or not isinstance(con, oracledb.Connection):
        raise TypeError(
            "`con` is required. Open one with open_clidatadb() and pass "
            "it in, e.g.\n"
            "  con = open_clidatadb()\n"
        )


def _stop_if_closed(e: Exception) -> None:
    """Raise a clear error when a call fails because `con` is closed.

    ORA-3113/ORA-1012 are Oracle's codes for a closed/invalid connection.
    No-op for any other error, letting the caller decide what to do.
    """
    msg = str(e)
    if "ORA-03113" in msg or "ORA-01012" in msg or "not connected" in msg:
        raise ConnectionError(
            "This connection is closed. Open a new one with "
            "open_clidatadb() and try again."
        ) from e


def _ibis_connect_from(con: oracledb.Connection) -> ibis.BaseBackend:
    cached = _ibis_cache.get(con)
    if cached is not None:
        return cached

    from .creds import get_user_creds

    # con.dsn is an Easy Connect string: "host:port/service_name"
    host_port, _, service_name = con.dsn.partition("/")
    host, _, port = host_port.partition(":")

    creds = get_user_creds(user=con.username)
    ibis_con = ibis.oracle.connect(
        user=creds["user"],
        password=creds["password"],
        host=host,
        port=int(port) if port else 1521,
        service_name=service_name,
    )
    _ibis_cache[con] = ibis_con
    return ibis_con


def _introspect_schema(
    con: oracledb.Connection, table: str, schema: str, ibis_con: ibis.BaseBackend
) -> ibis.Schema:
    """Build an ibis Schema for `schema.table` ourselves via ALL_TAB_COLUMNS.

    Ibis's own Oracle Backend.get_schema() computes "is nullable" as a
    boolean expression in the SELECT list (`nullable = 'Y' AS nullable`),
    which needs Oracle's native BOOLEAN type -- only available from 23c
    onward -- and raises ORA-00923 on any older Oracle Database (which is
    what CLIDATA, and most operational Oracle instances, run). This is a
    known ibis bug (ibis-project/ibis#10403). Worked around here by
    fetching the same metadata ourselves, comparing 'Y'/'N' in Python
    instead of in SQL, then reusing ibis's own (correct) Oracle
    type-mapping function.
    """
    cur = con.cursor()
    try:
        cur.execute(
            "SELECT column_name, data_type, data_precision, data_scale, nullable "
            "FROM all_tab_columns "
            "WHERE UPPER(owner) = UPPER(:schema) "
            "AND UPPER(table_name) = UPPER(:name) ORDER BY column_id",
            schema=schema,
            name=table,
        )
        rows = cur.fetchall()
    except oracledb.Error as e:
        _stop_if_closed(e)
        raise
    finally:
        cur.close()

    if not rows:
        raise LookupError(
            f"'{schema}.{table}' doesn't exist, or you don't have "
            "privileges on it. Call list_tables(con) or list_views(con) "
            "to see what's available."
        )

    type_mapper = ibis_con.compiler.type_mapper
    fields = {
        col_name: metadata_row_to_type(
            type_mapper=type_mapper,
            type_string=data_type,
            precision=precision,
            scale=scale,
            nullable=(nullable_flag == "Y"),
        )
        for col_name, data_type, precision, scale, nullable_flag in rows
    }
    return ibis.schema(fields)


def get_table(
    table: str,
    schema: str | None = None,
    con: oracledb.Connection | None = None,
) -> ibis.expr.types.Table:
    """Get a CLIDATA/Oracle table or view as a lazy ibis Table.

    Nothing is fetched until you materialize it. Chain
    `.filter(...)`/`.select(...)`/`.limit(...)` first -- those get
    pushed down to SQL -- then call `.to_pandas()`/`.execute()`.

    Args:
        table: Table or view name, e.g. "V_DAY_ALL_NULL". May also be
            schema-qualified (e.g. "CLIDATA.V_DAY_ALL_NULL"), in which
            case `schema` is ignored.
        schema: Oracle schema owning `table`. Defaults to the current
            CLIDATA service name (see get_host()).
        con: An oracledb.Connection, e.g. from open_clidatadb().

    Returns:
        A lazy ibis Table expression.
    """
    from .host import get_host

    if not table:
        raise ValueError("`table` is required, e.g. get_table('V_DAY_ALL_NULL')")
    _check_con(con)

    if "." in table:
        tbl_schema, tbl_name = table.split(".", 1)
    else:
        tbl_schema = schema if schema is not None else get_host()["service"]
        tbl_name = table

    ibis_con = _ibis_connect_from(con)
    ibis_schema = _introspect_schema(con, tbl_name, tbl_schema, ibis_con)
    return ops.DatabaseTable(
        tbl_name,
        schema=ibis_schema,
        source=ibis_con,
        namespace=ops.Namespace(catalog=None, database=tbl_schema),
    ).to_expr()


def list_tables(
    con: oracledb.Connection, schema: str | None = None
) -> list[str]:
    """List tables in an Oracle schema.

    Queries Oracle's ALL_TABLES data dictionary view.

    Args:
        con: An oracledb.Connection, e.g. from open_clidatadb().
        schema: Oracle schema to list tables from (matched
            case-insensitively). Defaults to the current service name
            (see get_host()).

    Returns:
        list of table names.
    """
    from .host import get_host

    _check_con(con)
    if schema is None:
        schema = get_host()["service"]

    cur = con.cursor()
    try:
        cur.execute(
            "SELECT table_name FROM all_tables "
            "WHERE UPPER(owner) = UPPER(:schema) ORDER BY table_name",
            schema=schema,
        )
        return [row[0] for row in cur.fetchall()]
    except oracledb.Error as e:
        _stop_if_closed(e)
        raise
    finally:
        cur.close()


def list_views(
    con: oracledb.Connection, schema: str | None = None
) -> list[str]:
    """List views in an Oracle schema.

    Queries Oracle's ALL_VIEWS data dictionary view.

    Args:
        con: An oracledb.Connection, e.g. from open_clidatadb().
        schema: Oracle schema to list views from (matched
            case-insensitively). Defaults to the current service name
            (see get_host()).

    Returns:
        list of view names.
    """
    from .host import get_host

    _check_con(con)
    if schema is None:
        schema = get_host()["service"]

    cur = con.cursor()
    try:
        cur.execute(
            "SELECT view_name FROM all_views "
            "WHERE UPPER(owner) = UPPER(:schema) ORDER BY view_name",
            schema=schema,
        )
        return [row[0] for row in cur.fetchall()]
    except oracledb.Error as e:
        _stop_if_closed(e)
        raise
    finally:
        cur.close()


def list_variables(
    table: str | pd.DataFrame | ibis.expr.types.Table,
    con: oracledb.Connection | None = None,
    schema: str | None = None,
) -> list[str]:
    """List the variables (columns) of a table/view.

    Args:
        table: Either a table/view name (str, e.g. "V_DAY_ALL_NULL" --
            `con` is then required, and Oracle's ALL_TAB_COLUMNS data
            dictionary view is queried directly, which covers both
            tables and views), or a get_table() result (a lazy ibis
            Table).
        con: An oracledb.Connection, e.g. from open_clidatadb(). Only
            used (and required) when `table` is a string name.
        schema: Oracle schema owning `table` (only used when `table` is
            a string name and isn't already schema-qualified, e.g.
            "CLIDATA.V_DAY_ALL_NULL"). Defaults to the current CLIDATA
            service name (see get_host()).

    Returns:
        list of column names.
    """
    from .host import get_host

    if not isinstance(table, str):
        return list(table.columns)

    _check_con(con)
    if "." in table:
        tbl_schema, tbl_name = table.split(".", 1)
    else:
        tbl_schema = schema if schema is not None else get_host()["service"]
        tbl_name = table

    cur = con.cursor()
    try:
        cur.execute(
            "SELECT column_name FROM all_tab_columns "
            "WHERE UPPER(owner) = UPPER(:schema) "
            "AND UPPER(table_name) = UPPER(:name) ORDER BY column_id",
            schema=tbl_schema,
            name=tbl_name,
        )
        cols = [row[0] for row in cur.fetchall()]
    except oracledb.Error as e:
        _stop_if_closed(e)
        raise
    finally:
        cur.close()

    if not cols:
        raise LookupError(
            f"'{tbl_schema}.{tbl_name}' doesn't exist, or you don't have "
            "privileges on it. Call list_tables(con) or list_views(con) "
            "to see what's available."
        )
    return cols

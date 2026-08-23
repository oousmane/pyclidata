"""Internal validation helpers, used by tables.py's public functions.

Python port of rclidata's checks.R. rclidata distinguishes a generic DBI
connection/tbl from one specifically backed by JDBC (RJDBC), since it
can sit on top of several DBI backends. pyclidata has no such
distinction to preserve -- open_clidatadb()/open_oracledb() only ever
produce an oracledb.Connection, and get_table() only ever produces a
lazy ibis.Table backed by it -- so there is a single pair of checks
here rather than a generic/JDBC-specific pair.
"""

from __future__ import annotations

from typing import Any

import ibis
import oracledb


def is_connection(x: Any) -> bool:
    """Is `x` an open connection, e.g. from open_clidatadb()?"""
    return isinstance(x, oracledb.Connection)


def is_lazy_table(x: Any) -> bool:
    """Is `x` a lazy remote table, e.g. from get_table()?"""
    return isinstance(x, ibis.Table)


def check_connection(x: Any, arg: str = "con") -> Any:
    """Validate that `x` is an open connection.

    Intended for use at the top of functions that expect a live
    connection rather than a lazy table.

    Args:
        x: Object to validate.
        arg: Argument name to use in the error message.

    Returns:
        `x`, unchanged.

    Raises:
        TypeError: If `x` isn't an oracledb.Connection.
    """
    if not is_connection(x):
        raise TypeError(
            f"`{arg}` must be an open connection (e.g. from "
            f"open_clidatadb()), not {type(x).__name__}."
        )
    return x


def check_table(x: Any, arg: str = "x") -> Any:
    """Validate that `x` is a lazy remote table.

    Intended for use at the top of functions that expect a
    `get_table()` result rather than a live connection.

    Args:
        x: Object to validate.
        arg: Argument name to use in the error message.

    Returns:
        `x`, unchanged.

    Raises:
        TypeError: If `x` isn't a lazy ibis table.
    """
    if not is_lazy_table(x):
        raise TypeError(
            f"`{arg}` must be a remote table (e.g. from get_table()), "
            f"not {type(x).__name__}."
        )
    return x

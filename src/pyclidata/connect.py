"""Open/close a connection to CLIDATA, or most any Oracle database.

Uses python-oracledb, which needs no JDK and no driver jar -- unlike the
R package's RJDBC-based approach, there is nothing to manually install
beyond `pixi install`. By default it runs in pure-Python "thin" mode.
Some Oracle accounts (e.g. CLIDATA's own, on a legacy pre-11G password
verifier) can't authenticate over thin mode at all (oracledb error
DPY-3015) -- only "thick" mode, backed by the native Oracle Instant
Client, supports those. This module auto-upgrades to thick mode if an
Instant Client is available (installed via the `oracle-instant-client`
conda package on platforms that support it -- see pyproject.toml) and
silently stays in thin mode otherwise, following python-oracledb's own
documented pattern for this.
"""

from __future__ import annotations

import glob
import os
from typing import Any

import oracledb

from .creds import get_user_creds
from .host import get_host


def _init_thick_mode_if_available() -> None:
    """Best-effort switch to thick mode; must run before any connection
    is opened in this process -- thin vs. thick is a process-wide
    setting in python-oracledb that can't be changed afterward.
    """
    lib_dir = None
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        candidates = sorted(
            glob.glob(
                os.path.join(conda_prefix, "oracle_instant_client", "instantclient_*")
            )
        )
        if candidates:
            lib_dir = candidates[-1]

    try:
        oracledb.init_oracle_client(lib_dir=lib_dir)
    except Exception:
        pass  # no usable Instant Client found -- stay in thin mode


_init_thick_mode_if_available()


def open_clidatadb(user: str | None = None) -> oracledb.Connection:
    """Open a connection to CLIDATA, or most any Oracle database.

    Builds an Oracle connection using credentials from get_user_creds()
    and the connection target from get_host(). The connection itself is
    a standard Oracle Net connection -- nothing about it is
    CLIDATA-specific beyond the default host/service (see set_host()) --
    so it works against most any Oracle database you have credentials
    for, not just CLIDATA.

    Args:
        user: Passed to get_user_creds(); defaults to the CLIDATA_USER
            env var (the last user persisted via set_user_creds()).

    Returns:
        An open oracledb.Connection, ready to use with `.cursor()` or
        pandas.read_sql().
    """
    creds = get_user_creds(user=user)
    host_info = get_host()

    dsn = f"{host_info['host']}:{host_info['port']}/{host_info['service']}"

    try:
        return oracledb.connect(
            user=creds["user"], password=creds["password"], dsn=dsn
        )
    except oracledb.Error as e:
        raise ConnectionError(
            f"Failed to connect to CLIDATA at {dsn} as user "
            f"'{creds['user']}': {e}"
        ) from e


def close_clidatadb(con: Any) -> None:
    """Close a connection returned by open_clidatadb()/open_oracledb().

    Args:
        con: An oracledb.Connection.
    """
    if not isinstance(con, oracledb.Connection):
        raise TypeError(
            "`con` is not an oracledb.Connection object. There is nothing "
            "to close."
        )
    con.close()


# Aliases under a more general name -- open_clidatadb()/close_clidatadb()
# work against most any Oracle database, not just CLIDATA (see module
# docstring); these are provided for that more general use.
open_oracledb = open_clidatadb
close_oracledb = close_clidatadb

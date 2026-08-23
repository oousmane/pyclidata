"""Open/close a connection to CLIDATA, or most any Oracle database.

Uses python-oracledb -- no JDK or driver jar required. Some Oracle
accounts (e.g. CLIDATA's own) need an extra one-time setup step to
connect at all; see the README's "Connection error: DPY-3015" section
if open_clidatadb() raises that.
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
    is opened -- thin vs. thick mode can't be changed later in the same
    process.
    """
    # Set by instantclient.install_instantclient() on Windows, where
    # thick mode has no automatic setup path (see below).
    lib_dir = os.environ.get("PYCLIDATA_INSTANT_CLIENT_DIR")

    if lib_dir is None:
        # macOS/Linux: set up automatically via the oracle-instant-client
        # conda package (pyproject.toml) inside a conda/pixi environment.
        conda_prefix = os.environ.get("CONDA_PREFIX")
        if conda_prefix:
            candidates = sorted(
                glob.glob(
                    os.path.join(
                        conda_prefix, "oracle_instant_client", "instantclient_*"
                    )
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
        hint = ""
        full_code = getattr(e.args[0], "full_code", "") if e.args else ""
        if full_code == "DPY-3015" and oracledb.is_thin_mode():
            hint = (
                " See the pyclidata README's 'Connection error: DPY-3015' "
                "section for how to fix this."
            )
        raise ConnectionError(
            f"Failed to connect to CLIDATA at {dsn} as user "
            f"'{creds['user']}': {e}{hint}"
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

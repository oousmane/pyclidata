"""pyclidata: connection helpers for a CLIDATA (or other) Oracle database.

Thin wrapper around python-oracledb to connect to a CLIDATA Oracle
database developed by ATACO. Uses oracledb's default "thin" mode, which
needs no Oracle Instant Client, no JDK, and no driver jar -- unlike the
sibling R package (rclidata), there is no separate Java/driver install
step at all.
"""

from __future__ import annotations

import sys

from ._config import load_config

# Must run before .connect is imported: connect.py auto-detects thick
# mode at import time, including via a PYCLIDATA_INSTANT_CLIENT_DIR
# persisted by instantclient.install_instantclient() -- that persisted
# value only reaches os.environ once load_config() has run.
load_config()

from .connect import close_clidatadb, close_oracledb, open_clidatadb, open_oracledb
from .creds import get_user_creds, set_user_creds
from .host import get_host, set_host
from .instantclient import install_instantclient
from .tables import get_table, list_tables, list_variables, list_views

__all__ = [
    "close_clidatadb",
    "close_oracledb",
    "get_host",
    "get_table",
    "get_user_creds",
    "install_instantclient",
    "list_tables",
    "list_variables",
    "list_views",
    "open_clidatadb",
    "open_oracledb",
    "set_host",
    "set_user_creds",
]

if sys.flags.interactive:
    print(
        "pyclidata -- first time?\n"
        "  Run set_user_creds('youruser') once to store your CLIDATA "
        "credentials.\n"
        "  Run set_host() if you're not connecting to the default "
        "'clidatadb1:1521/CLIDATA' instance.\n"
        "  No JDK/driver install needed -- python-oracledb runs in pure-"
        "Python thin mode."
    )

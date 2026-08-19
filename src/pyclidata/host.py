"""Connection target (host/port/service) for the CLIDATA/Oracle database."""

from __future__ import annotations

import os

from ._config import set_config

DEFAULTS = {"host": "clidatadb1", "port": "1521", "service": "CLIDATA"}


def set_host(
    host: str = DEFAULTS["host"],
    port: str | int = DEFAULTS["port"],
    service: str = DEFAULTS["service"],
    persist: bool = True,
) -> dict[str, str]:
    """Set the CLIDATA/Oracle connection target.

    Defaults to clidatadb1:1521/CLIDATA -- you only need this when
    connecting to a different instance (another institution's server, a
    test server, or any other Oracle database via open_oracledb()).

    Args:
        host: Hostname or IP address, e.g. "10.0.0.5".
        port: Port number.
        service: Oracle service name.
        persist: If True (default), also writes CLIDATA_HOST/CLIDATA_PORT/
            CLIDATA_SERVICE to the persisted config file so these values
            apply in every future session too, including non-interactive
            ones.

    Returns:
        dict with the host/port/service now in effect.
    """
    host, port, service = str(host), str(port), str(service)

    os.environ["CLIDATA_HOST"] = host
    os.environ["CLIDATA_PORT"] = port
    os.environ["CLIDATA_SERVICE"] = service

    if persist:
        set_config("CLIDATA_HOST", host)
        set_config("CLIDATA_PORT", port)
        set_config("CLIDATA_SERVICE", service)

    return get_host()


def get_host() -> dict[str, str]:
    """Get the current CLIDATA/Oracle connection target.

    Returns:
        dict with `host`, `port`, `service`, from set_host() (this session
        or a persisted past one), or the built-in defaults
        (clidatadb1:1521/CLIDATA) if set_host() was never called.
    """
    return {
        "host": os.environ.get("CLIDATA_HOST", DEFAULTS["host"]),
        "port": os.environ.get("CLIDATA_PORT", DEFAULTS["port"]),
        "service": os.environ.get("CLIDATA_SERVICE", DEFAULTS["service"]),
    }

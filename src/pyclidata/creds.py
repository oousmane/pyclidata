"""CLIDATA/Oracle user credential storage via the OS-native keyring."""

from __future__ import annotations

import getpass
import os

import keyring
import keyring.errors

from ._config import set_config

KEYRING_SERVICE = "pyclidata_clidata"


def set_user_creds(
    user: str, password: str | None = None, persist: bool = True
) -> str:
    """Store a CLIDATA/Oracle username/password pair securely.

    Uses the `keyring` package (OS-native credential store -- Windows
    Credential Manager, macOS Keychain, or the Secret Service on Linux).
    The password is never written to disk in plain text.

    Args:
        user: CLIDATA/Oracle username.
        password: If None (default), you'll be prompted securely (no
            echo) via getpass. Passing a literal password string works
            but is discouraged (it can end up in shell history/logs).
        persist: If True (default), also writes `user` (never the
            password) to the persisted config as CLIDATA_USER, so it's
            picked up automatically as the default user in future
            sessions, including non-interactive ones.

    Returns:
        The username that was set as current.
    """
    if not user:
        raise ValueError("`user` is required, e.g. set_user_creds('ousmane')")

    if password is None:
        password = getpass.getpass(f"Password for '{user}': ")

    keyring.set_password(KEYRING_SERVICE, user, password)

    os.environ["CLIDATA_USER"] = user
    print(
        f"Credentials stored for user '{user}' "
        f"(keyring service: '{KEYRING_SERVICE}')."
    )

    if persist:
        config_path = set_config("CLIDATA_USER", user)
        print(
            f"Username persisted to {config_path} -- "
            "the password itself stays only in the OS keyring."
        )

    return user


def get_user_creds(user: str | None = None) -> dict[str, str]:
    """Retrieve a previously stored username/password pair.

    Args:
        user: Username to look up. Defaults to the CLIDATA_USER env var
            (set by set_user_creds() this session, or persisted from a
            past one).

    Returns:
        dict with `user` and `password`.
    """
    if user is None:
        user = os.environ.get("CLIDATA_USER", "")
    if not user:
        raise ValueError(
            "No user set. Call set_user_creds(<user>) first, or pass "
            "`user` explicitly."
        )

    password = keyring.get_password(KEYRING_SERVICE, user)
    if password is None:
        raise LookupError(
            f"No stored credentials found for user '{user}'. "
            f"Call set_user_creds('{user}') first."
        )

    return {"user": user, "password": password}

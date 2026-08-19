"""Internal: persistent config storage, mirroring R's ~/.Renviron pattern.

R sources ~/.Renviron automatically at every startup, before any package
loads. Python has no equivalent, so pyclidata keeps its own dotenv file at
~/.config/pyclidata/config.env and loads it into os.environ as soon as the
package is imported (see __init__.py) -- so persisted values (CLIDATA_HOST,
CLIDATA_USER, etc.) are picked up automatically in every future session,
including non-interactive ones (scripts, cron), exactly like the R package.
"""

from __future__ import annotations

import os
from pathlib import Path

CONFIG_PATH = Path(
    os.environ.get("PYCLIDATA_CONFIG", "~/.config/pyclidata/config.env")
).expanduser()


def load_config() -> None:
    """Load persisted key=value pairs from CONFIG_PATH into os.environ.

    Existing os.environ values take precedence (matches dotenv's usual
    semantics), so an explicit env var set before import always wins over
    a persisted one.
    """
    if not CONFIG_PATH.exists():
        return
    for line in CONFIG_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"')
        os.environ.setdefault(key, value)


def set_config(key: str, value: str) -> Path:
    """Upsert a `KEY="value"` line in CONFIG_PATH, creating it if needed."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = (
        CONFIG_PATH.read_text().splitlines() if CONFIG_PATH.exists() else []
    )
    new_line = f'{key}="{value}"'
    replaced = False
    out = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            if not replaced:
                out.append(new_line)
                replaced = True
            # drop any duplicate matches, keep only the last one
        else:
            out.append(line)
    if not replaced:
        out.append(new_line)

    CONFIG_PATH.write_text("\n".join(out) + "\n")
    os.environ[key] = value
    return CONFIG_PATH

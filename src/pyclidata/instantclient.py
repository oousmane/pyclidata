"""Windows-only setup step to fix Oracle's DPY-3015 connection error.

See the README's "Connection error: DPY-3015" section for context --
macOS/Linux need no equivalent step; `pixi install` handles it there.
"""

from __future__ import annotations

import platform
import urllib.request
import zipfile
from pathlib import Path

from ._config import set_config

# Oracle Instant Client "Basic Light" for Windows x64. Oracle rotates
# these direct-download URLs across releases without a stable "latest"
# alias, so this default will eventually go stale -- if install_instantclient()
# fails to download, grab the current link yourself from
# https://www.oracle.com/database/technologies/instant-client/winx64-64-downloads.html
# and pass it as `url=`.
DEFAULT_URL = (
    "https://download.oracle.com/otn_software/nt/instantclient/2340000/"
    "instantclient-basiclite-windows.x64-23.4.0.24.05.zip"
)

DEFAULT_DEST = Path("~/.pyclidata/instantclient").expanduser()


def install_instantclient(
    url: str = DEFAULT_URL, dest: str | Path = DEFAULT_DEST, persist: bool = True
) -> Path:
    """Set up Oracle Instant Client on Windows (fixes DPY-3015 errors).

    Only needed on Windows, and only if connecting fails with a
    `DPY-3015` error -- see the README's "Connection error: DPY-3015"
    section.

    Args:
        url: Direct download link for an Instant Client Windows x64 ZIP.
            Only needed if the built-in default link stops working --
            get a current one from
            https://www.oracle.com/database/technologies/instant-client/winx64-64-downloads.html.
        dest: Where to install it. Defaults to ~/.pyclidata/instantclient.
        persist: If True (default), remembers this setup for future
            Python sessions too, so you only need to run this once.

    Returns:
        Path to the installed Instant Client.
    """
    if platform.system() != "Windows":
        raise NotImplementedError(
            "install_instantclient() is only needed on Windows -- on "
            "macOS/Linux, `pixi install` already sets this up for you."
        )

    dest = Path(dest).expanduser()
    dest.mkdir(parents=True, exist_ok=True)

    zip_path = dest / "instantclient.zip"
    print(f"Downloading Oracle Instant Client from {url} ...")
    try:
        urllib.request.urlretrieve(url, zip_path)
    except OSError as e:
        raise RuntimeError(
            f"Couldn't download Oracle Instant Client: {e}. Get a current "
            "download link from https://www.oracle.com/database/"
            "technologies/instant-client/winx64-64-downloads.html and "
            "pass it as `url=`."
        ) from e

    if not zipfile.is_zipfile(zip_path):
        zip_path.unlink()
        raise RuntimeError(
            "The downloaded file isn't a valid ZIP -- this download link "
            "has likely stopped working. Get a current one from "
            "https://www.oracle.com/database/technologies/instant-client/"
            "winx64-64-downloads.html and pass it as `url=`."
        )

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)
    zip_path.unlink()

    client_dirs = [
        p for p in dest.iterdir() if p.is_dir() and p.name.startswith("instantclient")
    ]
    if not client_dirs:
        raise RuntimeError(
            f"Extracted {url} into {dest}, but found no instantclient_* "
            "folder inside -- the archive layout may have changed."
        )
    client_dir = client_dirs[0]

    if persist:
        set_config("PYCLIDATA_INSTANT_CLIENT_DIR", str(client_dir))

    print(
        f"Oracle Instant Client installed at {client_dir}.\n"
        "Close this Python session completely and open a new one before "
        "connecting -- it won't take effect in this session."
    )
    return client_dir

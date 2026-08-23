import platform
import zipfile

import pytest

from pyclidata import instantclient


def _write_fake_instantclient_zip(zip_path, client_dir_name="instantclient_23_4"):
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(f"{client_dir_name}/oci.dll", b"not a real binary")


def test_install_instantclient_raises_on_non_windows(monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Darwin")

    with pytest.raises(NotImplementedError):
        instantclient.install_instantclient()


def test_install_instantclient_downloads_extracts_and_returns_path(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    fake_download = tmp_path / "source.zip"
    _write_fake_instantclient_zip(fake_download)

    def _fake_urlretrieve(url, filename):
        filename_path = filename if hasattr(filename, "read_bytes") else filename
        with open(fake_download, "rb") as src, open(filename_path, "wb") as dst:
            dst.write(src.read())

    monkeypatch.setattr(instantclient.urllib.request, "urlretrieve", _fake_urlretrieve)

    dest = tmp_path / "ic"
    client_dir = instantclient.install_instantclient(dest=dest, persist=False)

    assert client_dir == dest / "instantclient_23_4"
    assert (client_dir / "oci.dll").exists()
    assert not (dest / "instantclient.zip").exists()


def test_install_instantclient_persists_when_requested(monkeypatch, tmp_path):
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    fake_download = tmp_path / "source.zip"
    _write_fake_instantclient_zip(fake_download)

    def _fake_urlretrieve(url, filename):
        with open(fake_download, "rb") as src, open(filename, "wb") as dst:
            dst.write(src.read())

    monkeypatch.setattr(instantclient.urllib.request, "urlretrieve", _fake_urlretrieve)

    recorded = {}

    def _fake_set_config(key, value):
        recorded[key] = value
        return tmp_path / "config.env"

    monkeypatch.setattr(instantclient, "set_config", _fake_set_config)

    dest = tmp_path / "ic"
    client_dir = instantclient.install_instantclient(dest=dest, persist=True)

    assert recorded == {"PYCLIDATA_INSTANT_CLIENT_DIR": str(client_dir)}


def test_install_instantclient_rejects_non_zip_response(monkeypatch, tmp_path):
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    def _fake_urlretrieve(url, filename):
        with open(filename, "wb") as dst:
            dst.write(b"<html>not found</html>")

    monkeypatch.setattr(instantclient.urllib.request, "urlretrieve", _fake_urlretrieve)

    with pytest.raises(RuntimeError, match="valid ZIP"):
        instantclient.install_instantclient(dest=tmp_path / "ic", persist=False)

"""Empaquetado y operación local: respaldo y restauración (SQLite)."""
from __future__ import annotations


def test_respaldo_y_restauracion(tmp_path, monkeypatch):
    from app.config import settings
    from scripts import respaldo

    monkeypatch.chdir(tmp_path)
    db = tmp_path / "contratos.db"
    db.write_bytes(b"version-1")
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db.as_posix()}")

    respaldo.crear()
    copias = list((tmp_path / "respaldos").glob("backup_*.db"))
    assert len(copias) == 1
    assert copias[0].read_bytes() == b"version-1"

    db.write_bytes(b"version-2")
    respaldo.restaurar(str(copias[0]))
    assert db.read_bytes() == b"version-1"
    assert (tmp_path / "contratos.db.antes_de_restaurar").read_bytes() == b"version-2"

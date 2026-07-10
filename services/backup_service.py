import io
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd

from db.database import DB_PATH, get_engine, reset_engine

SQLITE_MAGIC = b"SQLite format 3\x00"
EXPECTED_TABLES = {"trainer", "termin", "anmeldung"}


class InvalidBackupFileError(Exception):
    pass


def _checkpoint_wal() -> None:
    """Schreibt ausstehende WAL-Änderungen in die Haupt-.db-Datei, bevor ihre Bytes gelesen werden."""
    with get_engine().connect() as conn:
        conn.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")


def export_db_bytes() -> bytes:
    _checkpoint_wal()
    return DB_PATH.read_bytes()


def export_csv_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        with get_engine().connect() as conn:
            for table in EXPECTED_TABLES:
                df = pd.read_sql_table(table, conn)
                zf.writestr(f"{table}.csv", df.to_csv(index=False))
    buffer.seek(0)
    return buffer.getvalue()


def _validate_sqlite_bytes(data: bytes) -> None:
    if not data.startswith(SQLITE_MAGIC):
        raise InvalidBackupFileError("Die Datei ist keine gültige SQLite-Datenbank.")

    tmp_path = DB_PATH.parent / f"_restore_check_{datetime.now():%Y%m%d%H%M%S}.db"
    tmp_path.write_bytes(data)
    try:
        conn = sqlite3.connect(tmp_path)
        try:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
        finally:
            conn.close()
    finally:
        tmp_path.unlink(missing_ok=True)

    if not EXPECTED_TABLES.issubset(tables):
        missing = EXPECTED_TABLES - tables
        raise InvalidBackupFileError(
            f"Die Datei enthält nicht die erwarteten Tabellen (fehlen: {', '.join(sorted(missing))})."
        )


def restore_from_upload(data: bytes) -> Path:
    """Validiert und übernimmt einen DB-Upload. Gibt den Pfad des Sicherheits-Backups zurück."""
    _validate_sqlite_bytes(data)

    safety_copy_path = DB_PATH.parent / f"trailpark_pre_restore_{datetime.now():%Y%m%d%H%M%S}.db"
    if DB_PATH.exists():
        _checkpoint_wal()
        safety_copy_path.write_bytes(DB_PATH.read_bytes())

    reset_engine()
    DB_PATH.write_bytes(data)
    reset_engine()

    return safety_copy_path

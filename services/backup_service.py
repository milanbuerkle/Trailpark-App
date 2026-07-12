import csv
import io
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path

from db.database import DB_PATH, get_engine, reset_engine

SQLITE_MAGIC = b"SQLite format 3\x00"
EXPECTED_TABLES = {"trainer", "termin", "anmeldung"}
CSV_EXPORT_TABLES = EXPECTED_TABLES | {"teilnahme"}


class InvalidBackupFileError(Exception):
    pass


def _wal_sidecar_paths() -> list[Path]:
    return [DB_PATH.with_name(DB_PATH.name + "-wal"), DB_PATH.with_name(DB_PATH.name + "-shm")]


def export_db_bytes() -> bytes:
    return DB_PATH.read_bytes()


def export_csv_zip() -> bytes:
    """Exportiert alle Tabellen als CSV, bewusst ohne pandas/pyarrow – reine
    SQL+csv-Modul-Lösung, um Crashes durch pyarrows C-Erweiterung auf noch
    nicht vollständig unterstützten Python-Versionen (z.B. sehr neue
    Python-Releases auf Streamlit Cloud) zu vermeiden."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        with get_engine().connect() as conn:
            for table in CSV_EXPORT_TABLES:
                result = conn.exec_driver_sql(f"SELECT * FROM {table}")
                columns = list(result.keys())
                rows = result.fetchall()

                csv_buffer = io.StringIO()
                writer = csv.writer(csv_buffer)
                writer.writerow(columns)
                writer.writerows(rows)
                zf.writestr(f"{table}.csv", csv_buffer.getvalue())
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
        safety_copy_path.write_bytes(DB_PATH.read_bytes())

    reset_engine()

    # Alte -wal/-shm-Nebendateien entfernen, damit keine veralteten WAL-Daten
    # (z.B. von einer noch im WAL-Modus laufenden alten Datenbank) mit der
    # gerade wiederhergestellten .db-Datei kollidieren.
    for sidecar in _wal_sidecar_paths():
        sidecar.unlink(missing_ok=True)

    DB_PATH.write_bytes(data)
    reset_engine()

    return safety_copy_path

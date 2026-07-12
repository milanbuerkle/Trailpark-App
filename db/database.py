import tempfile
from contextlib import contextmanager
from pathlib import Path

import streamlit as st
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base


def _resolve_data_dir() -> Path:
    """Nutzt den Projekt-Ordner `data/`, falls beschreibbar (lokale Entwicklung).

    Auf manchen Hosting-Umgebungen (z.B. Streamlit Community Cloud) ist der
    aus Git geklonte Projektordner read-only – dort weicht die App auf ein
    beschreibbares Temp-Verzeichnis aus. Das Datenverzeichnis ist auf
    Streamlit Cloud ohnehin nicht dauerhaft (siehe Backup/Restore-Runbook im
    README), daher ist ein Temp-Ordner dort kein zusätzlicher Nachteil.
    """
    project_data_dir = Path(__file__).resolve().parent.parent / "data"
    try:
        project_data_dir.mkdir(parents=True, exist_ok=True)
        probe = project_data_dir / ".write_test"
        probe.touch()
        probe.unlink()
        return project_data_dir
    except OSError:
        fallback_dir = Path(tempfile.gettempdir()) / "trailpark_app_data"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir


DATA_DIR = _resolve_data_dir()
DB_PATH = DATA_DIR / "trailpark.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"


@st.cache_resource
def get_engine():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        # Bewusst kein WAL-Modus: bei dieser Größenordnung (wenige gleichzeitige
        # Nutzer) bringt WAL kaum Vorteile, hat aber wiederholt Probleme beim
        # Backup/Restore verursacht (separate -wal-Datei kann mit einer per
        # Restore ausgetauschten .db-Datei kollidieren). Der Default-Journal-
        # Modus hält die .db-Datei immer selbstständig konsistent.
        cursor = dbapi_connection.cursor()
        # journal_mode ist eine dauerhafte Eigenschaft der .db-Datei selbst –
        # explizit zurücksetzen, falls eine ältere Datenbank noch im WAL-Modus ist.
        cursor.execute("PRAGMA journal_mode=DELETE")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@st.cache_resource
def get_sessionmaker():
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


# Spalten, die nach dem initialen Tabellen-Anlegen ergänzt wurden. Wird für
# bestehende Datenbanken per ALTER TABLE nachgezogen, damit echte Daten bei
# Schema-Änderungen nicht durch Neuanlegen der DB verloren gehen.
_COLUMN_MIGRATIONS = [
    ("termin", "email_required", "BOOLEAN NOT NULL DEFAULT 0"),
    ("teilnahme", "email", "VARCHAR(255)"),
]


def _run_migrations(engine) -> None:
    with engine.begin() as conn:
        for table, column, ddl_type in _COLUMN_MIGRATIONS:
            existing_columns = {
                row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            }
            if column not in existing_columns:
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
    _run_migrations(engine)


@contextmanager
def get_session():
    session: Session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    """Verwirft die gecachte Engine/Sessionmaker, z.B. nach einem DB-Restore."""
    get_engine().dispose()
    get_engine.clear()
    get_sessionmaker.clear()

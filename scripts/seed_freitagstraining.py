"""Legt einmalig wöchentliche Freitags-Trainings an (ab dem nächsten Freitag bis
Jahresende). Kein Dauer-Scheduler – bei Bedarf für einen weiteren Zeitraum erneut
mit angepassten Konstanten ausführen. Idempotent: bereits vorhandene Termine mit
gleichem Titel+Datum werden übersprungen.

Aufruf: python scripts/seed_freitagstraining.py
"""
import sys
from datetime import date, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.database import get_session, init_db
from db.models import Termin, Trainer
from services.termin_service import create_termin

TITLE = "MTB Kids Training"
LOCATION = "Trailpark"
START_TIME = time(17, 0)
END_TIME = time(19, 0)
NEEDED_TRAINERS = 2
END_DATE = date(2026, 12, 31)


def _next_friday(from_date: date) -> date:
    days_until_friday = (4 - from_date.weekday()) % 7  # Montag=0 ... Freitag=4
    return from_date + timedelta(days=days_until_friday)


def main() -> None:
    init_db()

    with get_session() as session:
        admin = session.query(Trainer).filter_by(is_admin=True).first()
        if admin is None:
            print("Kein Admin-Account gefunden. App einmal starten, damit er angelegt wird.")
            return
        admin_id = admin.id

    created = 0
    skipped = 0
    current = _next_friday(date.today())
    while current <= END_DATE:
        with get_session() as session:
            exists = (
                session.query(Termin)
                .filter_by(title=TITLE, date=current)
                .first()
                is not None
            )
        if exists:
            skipped += 1
        else:
            create_termin(
                title=TITLE,
                description=None,
                termin_date=current,
                start_time=START_TIME,
                end_time=END_TIME,
                location=LOCATION,
                needed_trainers=NEEDED_TRAINERS,
                created_by_trainer_id=admin_id,
            )
            created += 1
        current += timedelta(days=7)

    print(f"Fertig: {created} Termine angelegt, {skipped} bereits vorhanden übersprungen.")


if __name__ == "__main__":
    main()

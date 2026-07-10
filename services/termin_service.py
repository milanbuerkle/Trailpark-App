from dataclasses import dataclass
from datetime import date, datetime, time

from db.database import get_session
from db.models import Anmeldung, Teilnahme, Termin, Trainer
from services.email_service import send_teilnahme_bestaetigung


class CapacityFullError(Exception):
    pass


class AlreadyRegisteredError(Exception):
    pass


class NotRegisteredError(Exception):
    pass


class NotCreatorError(Exception):
    pass


class TooManyUpcomingSignupsError(Exception):
    pass


class DuplicateTeilnahmeError(Exception):
    pass


MAX_UPCOMING_SIGNUPS = 3


@dataclass(frozen=True)
class TerminInfo:
    id: int
    title: str
    description: str | None
    date: date
    start_time: time
    end_time: time
    location: str
    needed_trainers: int
    email_required: bool
    created_by_trainer_id: int
    created_by_name: str
    registered_trainer_names: tuple[str, ...]
    teilnehmer: tuple[tuple[int, str, str | None], ...]

    @property
    def registered_count(self) -> int:
        return len(self.registered_trainer_names)

    @property
    def free_slots(self) -> int:
        return max(0, self.needed_trainers - self.registered_count)

    @property
    def is_full(self) -> bool:
        return self.registered_count >= self.needed_trainers

    @property
    def teilnehmer_count(self) -> int:
        return len(self.teilnehmer)


def _to_info(termin: Termin) -> TerminInfo:
    return TerminInfo(
        id=termin.id,
        title=termin.title,
        description=termin.description,
        date=termin.date,
        start_time=termin.start_time,
        end_time=termin.end_time,
        location=termin.location,
        needed_trainers=termin.needed_trainers,
        email_required=termin.email_required,
        created_by_trainer_id=termin.created_by_trainer_id,
        created_by_name=termin.ersteller.name,
        registered_trainer_names=tuple(a.trainer.name for a in termin.anmeldungen),
        teilnehmer=tuple((t.id, t.name, t.email) for t in termin.teilnahmen),
    )


def list_termine() -> list[TerminInfo]:
    with get_session() as session:
        termine = session.query(Termin).order_by(Termin.date, Termin.start_time).all()
        return [_to_info(t) for t in termine]


def get_termin(termin_id: int) -> TerminInfo | None:
    with get_session() as session:
        termin = session.get(Termin, termin_id)
        return _to_info(termin) if termin is not None else None


def _validate_termin_fields(title: str, location: str, start_time: time, end_time: time, needed_trainers: int) -> None:
    if not title.strip():
        raise ValueError("Titel darf nicht leer sein.")
    if not location.strip():
        raise ValueError("Ort darf nicht leer sein.")
    if end_time <= start_time:
        raise ValueError("Die Endzeit muss nach der Startzeit liegen.")
    if needed_trainers < 1:
        raise ValueError("Es wird mindestens 1 Trainer benötigt.")


def create_termin(
    title: str,
    description: str | None,
    termin_date: date,
    start_time: time,
    end_time: time,
    location: str,
    needed_trainers: int,
    created_by_trainer_id: int,
    email_required: bool = False,
) -> int:
    _validate_termin_fields(title, location, start_time, end_time, needed_trainers)

    with get_session() as session:
        termin = Termin(
            title=title.strip(),
            description=(description or "").strip() or None,
            date=termin_date,
            start_time=start_time,
            end_time=end_time,
            location=location.strip(),
            needed_trainers=needed_trainers,
            email_required=email_required,
            created_by_trainer_id=created_by_trainer_id,
        )
        session.add(termin)
        session.flush()
        return termin.id


def update_termin(
    termin_id: int,
    trainer_id: int,
    title: str,
    description: str | None,
    termin_date: date,
    start_time: time,
    end_time: time,
    location: str,
    needed_trainers: int,
    email_required: bool,
) -> None:
    _validate_termin_fields(title, location, start_time, end_time, needed_trainers)

    with get_session() as session:
        termin = session.get(Termin, termin_id)
        if termin is None:
            raise ValueError("Termin wurde nicht gefunden.")
        if termin.created_by_trainer_id != trainer_id:
            raise NotCreatorError()

        termin.title = title.strip()
        termin.description = (description or "").strip() or None
        termin.date = termin_date
        termin.start_time = start_time
        termin.end_time = end_time
        termin.location = location.strip()
        termin.needed_trainers = needed_trainers
        termin.email_required = email_required


def delete_termin(termin_id: int, trainer_id: int) -> None:
    with get_session() as session:
        termin = session.get(Termin, termin_id)
        if termin is None:
            return
        if termin.created_by_trainer_id != trainer_id:
            raise NotCreatorError()
        session.delete(termin)


def count_upcoming_signups(trainer_id: int) -> int:
    with get_session() as session:
        return (
            session.query(Anmeldung)
            .join(Termin, Anmeldung.termin_id == Termin.id)
            .filter(Anmeldung.trainer_id == trainer_id, Termin.date >= date.today())
            .count()
        )


def sign_up(termin_id: int, trainer_id: int) -> None:
    with get_session() as session:
        termin = session.get(Termin, termin_id)
        if termin is None:
            raise ValueError("Termin wurde nicht gefunden.")

        already = (
            session.query(Anmeldung)
            .filter_by(termin_id=termin_id, trainer_id=trainer_id)
            .first()
        )
        if already is not None:
            raise AlreadyRegisteredError()

        upcoming_signups = (
            session.query(Anmeldung)
            .join(Termin, Anmeldung.termin_id == Termin.id)
            .filter(Anmeldung.trainer_id == trainer_id, Termin.date >= date.today())
            .count()
        )
        if upcoming_signups >= MAX_UPCOMING_SIGNUPS:
            raise TooManyUpcomingSignupsError()

        registered_count = (
            session.query(Anmeldung).filter_by(termin_id=termin_id).count()
        )
        if registered_count >= termin.needed_trainers:
            raise CapacityFullError()

        session.add(Anmeldung(termin_id=termin_id, trainer_id=trainer_id))


def cancel_signup(termin_id: int, trainer_id: int) -> None:
    with get_session() as session:
        anmeldung = (
            session.query(Anmeldung)
            .filter_by(termin_id=termin_id, trainer_id=trainer_id)
            .first()
        )
        if anmeldung is None:
            raise NotRegisteredError()
        session.delete(anmeldung)


def teilnehmer_anmelden(termin_id: int, name: str, email: str | None = None) -> int:
    name = name.strip()
    email = (email or "").strip() or None
    if not name:
        raise ValueError("Name darf nicht leer sein.")

    with get_session() as session:
        termin = session.get(Termin, termin_id)
        if termin is None:
            raise ValueError("Termin wurde nicht gefunden.")

        if termin.email_required:
            if not email:
                raise ValueError("Für diesen Termin wird eine E-Mail-Adresse benötigt.")
            if "@" not in email or "." not in email.split("@")[-1]:
                raise ValueError("Bitte eine gültige E-Mail-Adresse angeben.")

        duplicate = any(t.name.strip().lower() == name.lower() for t in termin.teilnahmen)
        if duplicate:
            raise DuplicateTeilnahmeError()

        teilnahme = Teilnahme(termin_id=termin_id, name=name, email=email)
        session.add(teilnahme)
        session.flush()
        teilnahme_id = teilnahme.id
        termin_snapshot = (termin.title, termin.date, termin.start_time, termin.end_time, termin.location)

    if email:
        title, termin_date, start_time, end_time, location = termin_snapshot
        send_teilnahme_bestaetigung(email, name, title, termin_date, start_time, end_time, location)

    return teilnahme_id


def teilnehmer_entfernen(teilnahme_id: int) -> None:
    with get_session() as session:
        teilnahme = session.get(Teilnahme, teilnahme_id)
        if teilnahme is not None:
            session.delete(teilnahme)


def list_my_termine(trainer_id: int) -> tuple[list[TerminInfo], list[TerminInfo]]:
    """Gibt (erstellte Termine, angemeldete Termine) für einen Trainer zurück."""
    with get_session() as session:
        erstellt = (
            session.query(Termin)
            .filter_by(created_by_trainer_id=trainer_id)
            .order_by(Termin.date, Termin.start_time)
            .all()
        )
        angemeldet = (
            session.query(Termin)
            .join(Anmeldung)
            .filter(Anmeldung.trainer_id == trainer_id)
            .order_by(Termin.date, Termin.start_time)
            .all()
        )
        return [_to_info(t) for t in erstellt], [_to_info(t) for t in angemeldet]

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime

import bcrypt
import streamlit as st

from db.database import get_session
from db.models import Trainer

REMEMBER_TOKEN_BYTES = 32

OTP_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # ohne 0/O, 1/I/l zur besseren Lesbarkeit
OTP_LENGTH = 10


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class TrainerNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class TrainerAccountInfo:
    id: int
    name: str
    email: str
    is_admin: bool
    must_set_password: bool
    created_at: datetime


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def generate_one_time_password() -> str:
    return "".join(secrets.choice(OTP_ALPHABET) for _ in range(OTP_LENGTH))


def ensure_admin_seeded() -> None:
    """Legt den festen Admin-Account aus st.secrets an, falls er noch nicht existiert.

    Die Zugangsdaten stehen in .streamlit/secrets.toml (git-ignoriert), nicht im
    Quellcode. Ist dort nichts konfiguriert, wird kein Admin angelegt.
    """
    admin_name = st.secrets.get("admin_name")
    admin_email = st.secrets.get("admin_email")
    admin_password = st.secrets.get("admin_password")
    if not (admin_name and admin_email and admin_password):
        return

    admin_email = admin_email.strip().lower()

    with get_session() as session:
        if session.query(Trainer).filter_by(email=admin_email).first():
            return
        session.add(
            Trainer(
                name=admin_name,
                email=admin_email,
                password_hash=_hash_password(admin_password),
                is_admin=True,
                must_set_password=False,
            )
        )


def create_trainer_invite(name: str, email: str) -> tuple[int, str]:
    """Legt einen neuen Trainer-Account mit Einmalpasswort an. Gibt (trainer_id, otp) zurück."""
    name = name.strip()
    email = email.strip().lower()

    if not name:
        raise ValueError("Name darf nicht leer sein.")
    if not email:
        raise ValueError("E-Mail darf nicht leer sein.")

    otp = generate_one_time_password()

    with get_session() as session:
        if session.query(Trainer).filter_by(email=email).first():
            raise EmailAlreadyRegisteredError(email)

        trainer = Trainer(
            name=name,
            email=email,
            password_hash=_hash_password(otp),
            is_admin=False,
            must_set_password=True,
        )
        session.add(trainer)
        session.flush()
        return trainer.id, otp


def regenerate_invite(trainer_id: int) -> str:
    """Erzeugt ein neues Einmalpasswort für einen Trainer, der sein altes verloren hat."""
    otp = generate_one_time_password()
    with get_session() as session:
        trainer = session.get(Trainer, trainer_id)
        if trainer is None:
            raise TrainerNotFoundError()
        trainer.password_hash = _hash_password(otp)
        trainer.must_set_password = True
        return otp


def set_new_password(trainer_id: int, new_password: str) -> None:
    if len(new_password) < 8:
        raise ValueError("Das Passwort muss mindestens 8 Zeichen lang sein.")
    with get_session() as session:
        trainer = session.get(Trainer, trainer_id)
        if trainer is None:
            raise TrainerNotFoundError()
        trainer.password_hash = _hash_password(new_password)
        trainer.must_set_password = False
        trainer.remember_token_hash = None


def change_password(trainer_id: int, current_password: str, new_password: str) -> None:
    if len(new_password) < 8:
        raise ValueError("Das neue Passwort muss mindestens 8 Zeichen lang sein.")
    with get_session() as session:
        trainer = session.get(Trainer, trainer_id)
        if trainer is None:
            raise TrainerNotFoundError()
        if not bcrypt.checkpw(current_password.encode("utf-8"), trainer.password_hash.encode("utf-8")):
            raise InvalidCredentialsError()
        trainer.password_hash = _hash_password(new_password)
        trainer.remember_token_hash = None


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_remember_token(trainer_id: int) -> str:
    """Erzeugt ein neues Remember-Me-Token, speichert nur dessen Hash. Gibt den
    Klartext-Token zurück, der als Cookie-Wert gesetzt wird (nie in der DB)."""
    token = secrets.token_urlsafe(REMEMBER_TOKEN_BYTES)
    with get_session() as session:
        trainer = session.get(Trainer, trainer_id)
        if trainer is None:
            raise TrainerNotFoundError()
        trainer.remember_token_hash = _hash_token(token)
    return token


def authenticate_by_remember_token(token: str) -> int | None:
    if not token:
        return None
    with get_session() as session:
        trainer = session.query(Trainer).filter_by(remember_token_hash=_hash_token(token)).first()
        return trainer.id if trainer is not None else None


def clear_remember_token(trainer_id: int) -> None:
    with get_session() as session:
        trainer = session.get(Trainer, trainer_id)
        if trainer is not None:
            trainer.remember_token_hash = None


def list_trainers() -> list[TrainerAccountInfo]:
    with get_session() as session:
        trainers = session.query(Trainer).order_by(Trainer.name).all()
        return [
            TrainerAccountInfo(
                id=t.id,
                name=t.name,
                email=t.email,
                is_admin=t.is_admin,
                must_set_password=t.must_set_password,
                created_at=t.created_at,
            )
            for t in trainers
        ]


def authenticate_trainer(email: str, password: str) -> int:
    email = email.strip().lower()
    with get_session() as session:
        trainer = session.query(Trainer).filter_by(email=email).first()
        if trainer is None or not bcrypt.checkpw(
            password.encode("utf-8"), trainer.password_hash.encode("utf-8")
        ):
            raise InvalidCredentialsError()
        return trainer.id

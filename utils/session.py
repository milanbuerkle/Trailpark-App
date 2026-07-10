from dataclasses import dataclass

import streamlit as st

from db.database import get_session
from db.models import Trainer
from services.auth_service import authenticate_by_remember_token, clear_remember_token, issue_remember_token

REMEMBER_QUERY_PARAM = "rt"


@dataclass(frozen=True)
class CurrentTrainer:
    id: int
    name: str
    email: str
    is_admin: bool
    must_set_password: bool


def current_trainer() -> CurrentTrainer | None:
    trainer_id = st.session_state.get("trainer_id")
    if trainer_id is None:
        return None
    with get_session() as session:
        trainer = session.get(Trainer, trainer_id)
        if trainer is None:
            st.session_state.pop("trainer_id", None)
            return None
        return CurrentTrainer(
            id=trainer.id,
            name=trainer.name,
            email=trainer.email,
            is_admin=trainer.is_admin,
            must_set_password=trainer.must_set_password,
        )


def login(trainer_id: int) -> None:
    st.session_state["trainer_id"] = trainer_id


def logout() -> None:
    st.session_state.pop("trainer_id", None)


def set_remember_cookie(trainer_id: int) -> None:
    """Merkt den Login über einen URL-Parameter vor (kein Custom-Component nötig,
    dadurch keine Kollision mit der Kalender-Komponente möglich)."""
    token = issue_remember_token(trainer_id)
    st.query_params[REMEMBER_QUERY_PARAM] = token


def clear_remember_cookie(trainer_id: int) -> None:
    clear_remember_token(trainer_id)
    st.query_params.pop(REMEMBER_QUERY_PARAM, None)


def try_remember_login() -> None:
    """Loggt automatisch ein, falls die URL ein gültiges Remember-Me-Token enthält."""
    if st.session_state.get("trainer_id") is not None:
        return

    token = st.query_params.get(REMEMBER_QUERY_PARAM)
    if not token:
        return

    trainer_id = authenticate_by_remember_token(token)
    if trainer_id is not None:
        login(trainer_id)

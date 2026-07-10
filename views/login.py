import streamlit as st

from services.auth_service import (
    InvalidCredentialsError,
    authenticate_trainer,
    change_password,
)
from utils.session import clear_remember_cookie, current_trainer, login, logout, set_remember_cookie


def _render_login_form() -> None:
    st.info(
        "Neue Accounts werden vom Admin per Einmalpasswort angelegt – "
        "wende dich dazu an Milan."
    )
    with st.form("login_form"):
        email = st.text_input("E-Mail")
        password = st.text_input("Passwort", type="password")
        submitted = st.form_submit_button("Anmelden")
    if submitted:
        try:
            trainer_id = authenticate_trainer(email, password)
            login(trainer_id)
            set_remember_cookie(trainer_id)
            st.rerun()
        except InvalidCredentialsError:
            st.error("E-Mail oder Passwort ist falsch.")


def _render_logged_in(trainer) -> None:
    st.success(f"Angemeldet als **{trainer.name}** ({trainer.email})")
    if trainer.is_admin:
        st.caption("Diese/r Trainer/in hat Admin-Rechte.")
    if st.button("Abmelden"):
        clear_remember_cookie(trainer.id)
        logout()
        st.rerun()

    st.divider()
    st.subheader("Passwort ändern")
    with st.form("change_password_form"):
        current_password = st.text_input("Aktuelles Passwort", type="password")
        new_password = st.text_input("Neues Passwort (mind. 8 Zeichen)", type="password")
        new_password_repeat = st.text_input("Neues Passwort wiederholen", type="password")
        submitted = st.form_submit_button("Passwort ändern")
    if submitted:
        if new_password != new_password_repeat:
            st.error("Die neuen Passwörter stimmen nicht überein.")
        else:
            try:
                change_password(trainer.id, current_password, new_password)
                set_remember_cookie(trainer.id)
                st.success("Passwort wurde geändert.")
            except InvalidCredentialsError:
                st.error("Das aktuelle Passwort ist falsch.")
            except ValueError as exc:
                st.error(str(exc))


def render() -> None:
    st.title("Login")

    trainer = current_trainer()
    if trainer is not None:
        _render_logged_in(trainer)
        return

    _render_login_form()

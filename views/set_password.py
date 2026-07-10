import streamlit as st

from services.auth_service import set_new_password
from utils.session import current_trainer, set_remember_cookie


def render() -> None:
    st.title("Passwort festlegen")

    trainer = current_trainer()
    if trainer is None:
        st.info("Bitte melde dich zuerst mit deinem Einmalpasswort an.")
        return

    st.info(
        f"Willkommen, {trainer.name}! Bitte lege ein eigenes Passwort fest, "
        "bevor du die App weiter nutzen kannst."
    )

    with st.form("set_password_form"):
        new_password = st.text_input("Neues Passwort (mind. 8 Zeichen)", type="password")
        new_password_repeat = st.text_input("Neues Passwort wiederholen", type="password")
        submitted = st.form_submit_button("Passwort festlegen")

    if submitted:
        if new_password != new_password_repeat:
            st.error("Die Passwörter stimmen nicht überein.")
        else:
            try:
                set_new_password(trainer.id, new_password)
                set_remember_cookie(trainer.id)
                st.success("Passwort wurde festgelegt.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

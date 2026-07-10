import streamlit as st

from services.auth_service import (
    EmailAlreadyRegisteredError,
    create_trainer_invite,
    list_trainers,
    regenerate_invite,
)
from utils.session import current_trainer


def render() -> None:
    st.title("Trainer verwalten")

    trainer = current_trainer()
    if trainer is None or not trainer.is_admin:
        st.info("Diese Seite ist nur für Admins zugänglich.")
        return

    st.subheader("Neuen Trainer einladen")
    with st.form("invite_form"):
        name = st.text_input("Name")
        email = st.text_input("E-Mail")
        submitted = st.form_submit_button("Einladen")

    if submitted:
        try:
            _, otp = create_trainer_invite(name, email)
            st.success(f"Trainer **{name}** wurde angelegt.")
            st.info("Einmalpasswort (bitte sicher an die Person weitergeben):")
            st.code(otp)
        except EmailAlreadyRegisteredError:
            st.error("Diese E-Mail-Adresse ist bereits registriert.")
        except ValueError as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("Alle Trainer")
    for t in list_trainers():
        with st.container(border=True):
            status = "Admin" if t.is_admin else "Trainer"
            st.write(f"**{t.name}** ({t.email}) – {status}")
            if t.must_set_password:
                st.caption("Passwort noch ausstehend (Einmalpasswort nicht eingelöst).")
                if st.button("Neues Einmalpasswort erzeugen", key=f"regen_{t.id}"):
                    new_otp = regenerate_invite(t.id)
                    st.info("Neues Einmalpasswort (bitte sicher weitergeben):")
                    st.code(new_otp)
            else:
                st.caption("Passwort eingerichtet.")

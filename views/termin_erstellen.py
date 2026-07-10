from datetime import date, time

import streamlit as st

from services.termin_service import create_termin
from utils.session import current_trainer


def render() -> None:
    st.title("Termin erstellen")

    trainer = current_trainer()
    if trainer is None:
        st.info("Bitte melde dich an, um einen Termin zu erstellen.")
        return

    with st.form("termin_erstellen_form"):
        title = st.text_input("Titel des Kurses")
        description = st.text_area("Beschreibung (optional)")
        termin_date = st.date_input("Datum", min_value=date.today(), value=date.today())
        col1, col2 = st.columns(2)
        with col1:
            start_time = st.time_input("Startzeit", value=time(10, 0))
        with col2:
            end_time = st.time_input("Endzeit", value=time(12, 0))
        location = st.text_input("Ort")
        needed_trainers = st.number_input("Benötigte Trainer-Anzahl", min_value=1, value=2, step=1)
        teilnehmer_anmeldung = st.radio(
            "Wie sollen sich Teilnehmer anmelden?",
            options=["Nur Name", "Name + E-Mail"],
            index=0,
            horizontal=True,
        )
        submitted = st.form_submit_button("Termin anlegen")

    if submitted:
        try:
            create_termin(
                title=title,
                description=description,
                termin_date=termin_date,
                start_time=start_time,
                end_time=end_time,
                location=location,
                needed_trainers=int(needed_trainers),
                created_by_trainer_id=trainer.id,
                email_required=(teilnehmer_anmeldung == "Name + E-Mail"),
            )
            st.success("Termin wurde erfolgreich angelegt.")
        except ValueError as exc:
            st.error(str(exc))

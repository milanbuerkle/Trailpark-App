import streamlit as st

from services.termin_service import (
    NotCreatorError,
    NotRegisteredError,
    cancel_signup,
    delete_termin,
    list_my_termine,
    update_termin,
)
from utils.session import current_trainer


def _render_edit_form(termin, trainer_id: int) -> None:
    with st.expander("Bearbeiten"):
        with st.form(f"edit_termin_form_{termin.id}"):
            title = st.text_input("Titel des Kurses", value=termin.title)
            description = st.text_area("Beschreibung (optional)", value=termin.description or "")
            termin_date = st.date_input("Datum", value=termin.date)
            col1, col2 = st.columns(2)
            with col1:
                start_time = st.time_input("Startzeit", value=termin.start_time)
            with col2:
                end_time = st.time_input("Endzeit", value=termin.end_time)
            location = st.text_input("Ort", value=termin.location)
            needed_trainers = st.number_input(
                "Benötigte Trainer-Anzahl", min_value=1, value=termin.needed_trainers, step=1
            )
            teilnehmer_anmeldung = st.radio(
                "Wie sollen sich Teilnehmer anmelden?",
                options=["Nur Name", "Name + E-Mail"],
                index=1 if termin.email_required else 0,
                horizontal=True,
            )
            submitted = st.form_submit_button("Änderungen speichern")

        if submitted:
            try:
                update_termin(
                    termin_id=termin.id,
                    trainer_id=trainer_id,
                    title=title,
                    description=description,
                    termin_date=termin_date,
                    start_time=start_time,
                    end_time=end_time,
                    location=location,
                    needed_trainers=int(needed_trainers),
                    email_required=(teilnehmer_anmeldung == "Name + E-Mail"),
                )
                st.success("Termin wurde aktualisiert.")
                st.rerun()
            except NotCreatorError:
                st.error("Nur der/die Ersteller/in kann diesen Termin bearbeiten.")
            except ValueError as exc:
                st.error(str(exc))


def render() -> None:
    st.title("Meine Termine")

    trainer = current_trainer()
    if trainer is None:
        st.info("Bitte melde dich an, um deine Termine zu sehen.")
        return

    erstellt, angemeldet = list_my_termine(trainer.id)

    st.subheader("Von mir erstellte Termine")
    if not erstellt:
        st.caption("Du hast noch keine Termine erstellt.")
    for termin in erstellt:
        with st.container(border=True):
            st.write(
                f"**{termin.title}** – {termin.date.strftime('%d.%m.%Y')} "
                f"{termin.start_time.strftime('%H:%M')}–{termin.end_time.strftime('%H:%M')}, {termin.location}"
            )
            st.caption(f"{termin.registered_count} von {termin.needed_trainers} Plätzen belegt")
            _render_edit_form(termin, trainer.id)
            if st.button("Termin löschen", key=f"delete_{termin.id}"):
                delete_termin(termin.id, trainer.id)
                st.rerun()

    st.subheader("Meine Anmeldungen")
    if not angemeldet:
        st.caption("Du bist für keinen Termin angemeldet.")
    for termin in angemeldet:
        with st.container(border=True):
            st.write(
                f"**{termin.title}** – {termin.date.strftime('%d.%m.%Y')} "
                f"{termin.start_time.strftime('%H:%M')}–{termin.end_time.strftime('%H:%M')}, {termin.location}"
            )
            st.caption(f"{termin.registered_count} von {termin.needed_trainers} Plätzen belegt")
            if st.button("Abmelden", key=f"cancel_{termin.id}"):
                try:
                    cancel_signup(termin.id, trainer.id)
                    st.rerun()
                except NotRegisteredError:
                    st.error("Du bist für diesen Termin nicht angemeldet.")

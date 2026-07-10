from datetime import datetime

import streamlit as st
from streamlit_calendar import calendar

from services.termin_service import (
    MAX_UPCOMING_SIGNUPS,
    AlreadyRegisteredError,
    CapacityFullError,
    DuplicateTeilnahmeError,
    NotRegisteredError,
    TooManyUpcomingSignupsError,
    cancel_signup,
    count_upcoming_signups,
    get_termin,
    list_termine,
    sign_up,
    teilnehmer_anmelden,
    teilnehmer_entfernen,
)
from utils.session import current_trainer

FARBE_GESUCHT = "#e63946"  # niemand angemeldet
FARBE_TEILWEISE = "#f4a261"  # teilweise belegt
FARBE_VOLL = "#2a9d8f"  # voll besetzt

CALENDAR_CSS = """
.fc {
    font-family: "Source Sans Pro", sans-serif;
}
.fc .fc-toolbar-title {
    font-size: 1.25rem;
    font-weight: 600;
}
.fc .fc-button {
    border-radius: 6px !important;
    text-transform: none !important;
    box-shadow: none !important;
    padding: 0.35rem 0.75rem !important;
}
.fc .fc-daygrid-day-number, .fc .fc-col-header-cell-cushion {
    font-size: 0.85rem;
    opacity: 0.85;
}
.fc-event {
    border: none !important;
    border-radius: 6px !important;
    padding: 1px 4px !important;
    font-size: 0.82rem !important;
    cursor: pointer;
}
.fc-daygrid-day.fc-day-today, .fc-timegrid-col.fc-day-today {
    background-color: rgba(42, 157, 143, 0.08) !important;
}
"""

LEGENDE_HTML = """
<div style="display:flex; gap:1.5rem; flex-wrap:wrap; margin:0.25rem 0 1rem 0; font-size:0.9rem;">
  <span><span style="display:inline-block;width:10px;height:10px;border-radius:50%;
    background:{gesucht};margin-right:6px;"></span>Kein Trainer angemeldet</span>
  <span><span style="display:inline-block;width:10px;height:10px;border-radius:50%;
    background:{teilweise};margin-right:6px;"></span>Teilweise belegt</span>
  <span><span style="display:inline-block;width:10px;height:10px;border-radius:50%;
    background:{voll};margin-right:6px;"></span>Voll besetzt</span>
</div>
""".format(gesucht=FARBE_GESUCHT, teilweise=FARBE_TEILWEISE, voll=FARBE_VOLL)


def _termin_farbe(registered_count: int, needed: int) -> str:
    if registered_count == 0:
        return FARBE_GESUCHT
    if registered_count < needed:
        return FARBE_TEILWEISE
    return FARBE_VOLL


def _build_events() -> list[dict]:
    events = []
    for termin in list_termine():
        start = datetime.combine(termin.date, termin.start_time).isoformat()
        end = datetime.combine(termin.date, termin.end_time).isoformat()
        farbe = _termin_farbe(termin.registered_count, termin.needed_trainers)
        events.append(
            {
                "id": str(termin.id),
                "title": f"{termin.title} ({termin.registered_count}/{termin.needed_trainers})",
                "start": start,
                "end": end,
                "backgroundColor": farbe,
                "borderColor": farbe,
            }
        )
    return events


def _close_dialog() -> None:
    st.session_state["selected_termin_id"] = None


@st.dialog("Termin-Details", on_dismiss=_close_dialog)
def _termin_dialog(termin_id: int) -> None:
    termin = get_termin(termin_id)
    if termin is None:
        st.warning("Dieser Termin existiert nicht mehr.")
        if st.button("Schließen"):
            st.session_state["selected_termin_id"] = None
            st.rerun()
        return

    st.subheader(termin.title)
    st.markdown(
        f"📅 {termin.date.strftime('%d.%m.%Y')}  \n"
        f"🕐 {termin.start_time.strftime('%H:%M')} – {termin.end_time.strftime('%H:%M')} Uhr  \n"
        f"📍 {termin.location}"
    )
    if termin.description:
        st.caption(termin.description)
    st.caption(f"Erstellt von {termin.created_by_name}")

    st.divider()
    st.write(f"**{termin.registered_count} von {termin.needed_trainers} Plätzen belegt**")
    st.progress(min(1.0, termin.registered_count / termin.needed_trainers))
    if termin.registered_trainer_names:
        for name in termin.registered_trainer_names:
            st.write(f"- {name}")
    else:
        st.caption("Noch kein Trainer angemeldet.")

    trainer = current_trainer()
    if trainer is not None:
        st.divider()
        is_registered = trainer.name in termin.registered_trainer_names
        if is_registered:
            if st.button("Abmelden"):
                try:
                    cancel_signup(termin.id, trainer.id)
                    st.rerun()
                except NotRegisteredError:
                    st.error("Du bist für diesen Termin nicht angemeldet.")
        elif termin.is_full:
            st.warning("Termin ist bereits voll besetzt.")
        else:
            upcoming = count_upcoming_signups(trainer.id)
            st.caption(f"Du bist für {upcoming} von {MAX_UPCOMING_SIGNUPS} möglichen kommenden Terminen angemeldet.")
            if st.button("Anmelden"):
                try:
                    sign_up(termin.id, trainer.id)
                    st.rerun()
                except CapacityFullError:
                    st.warning("Termin ist bereits voll besetzt.")
                except AlreadyRegisteredError:
                    st.error("Du bist bereits für diesen Termin angemeldet.")
                except TooManyUpcomingSignupsError:
                    st.warning(
                        f"Du bist bereits für {MAX_UPCOMING_SIGNUPS} kommende Termine angemeldet. "
                        "Bitte warte, bis einer davon stattgefunden hat, oder melde dich von einem "
                        "anderen Termin ab, damit auch andere Trainer eine Chance bekommen."
                    )

    st.divider()
    st.subheader(f"Teilnehmer ({termin.teilnehmer_count})")
    if termin.email_required:
        st.caption("Bei diesem Termin wird zusätzlich eine E-Mail-Adresse benötigt.")
    if termin.teilnehmer:
        for teilnahme_id, name, email in termin.teilnehmer:
            col_name, col_remove = st.columns([5, 1])
            label = f"- {name}" + (f" ({email})" if email and trainer is not None else "")
            col_name.write(label)
            if trainer is not None:
                if col_remove.button("✕", key=f"remove_teilnehmer_{teilnahme_id}"):
                    teilnehmer_entfernen(teilnahme_id)
                    st.rerun()
    else:
        st.caption("Noch kein Teilnehmer angemeldet.")

    with st.form(f"teilnehmer_form_{termin.id}", clear_on_submit=True):
        teilnehmer_name = st.text_input("Dein Name")
        teilnehmer_email = st.text_input("Deine E-Mail") if termin.email_required else ""
        teilnehmer_submitted = st.form_submit_button("Als Teilnehmer anmelden")
    if teilnehmer_submitted:
        try:
            teilnehmer_anmelden(termin.id, teilnehmer_name, teilnehmer_email)
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except DuplicateTeilnahmeError:
            st.info("Du stehst schon auf der Liste.")

    if st.button("Schließen"):
        st.session_state["selected_termin_id"] = None
        st.rerun()


def render() -> None:
    st.title("Kalender")
    st.markdown(LEGENDE_HTML, unsafe_allow_html=True)

    options = {
        "initialView": "dayGridMonth",
        "locale": "de",
        "firstDay": 1,
        "height": 650,
        "displayEventTime": False,
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,listMonth",
        },
        "buttonText": {
            "today": "Heute",
            "month": "Monat",
            "week": "Woche",
            "list": "Liste",
        },
    }

    calendar_result = calendar(
        events=_build_events(), options=options, custom_css=CALENDAR_CSS, key="kalender"
    )

    if calendar_result.get("callback") == "eventClick":
        if calendar_result != st.session_state.get("_last_calendar_result"):
            st.session_state["_last_calendar_result"] = calendar_result
            st.session_state["selected_termin_id"] = int(
                calendar_result["eventClick"]["event"]["id"]
            )

    selected_id = st.session_state.get("selected_termin_id")
    if selected_id:
        _termin_dialog(selected_id)

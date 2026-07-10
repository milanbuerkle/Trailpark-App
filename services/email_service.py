import smtplib
from datetime import date, time
from email.message import EmailMessage

import streamlit as st


def _smtp_config() -> dict | None:
    host = st.secrets.get("smtp_host")
    port = st.secrets.get("smtp_port")
    user = st.secrets.get("smtp_user")
    password = st.secrets.get("smtp_password")
    from_email = st.secrets.get("smtp_from_email", user)
    if not (host and port and user and password and from_email):
        return None
    return {
        "host": host,
        "port": int(port),
        "user": user,
        "password": password,
        "from_email": from_email,
        "from_name": st.secrets.get("smtp_from_name", "MTB Verein"),
    }


def send_teilnahme_bestaetigung(
    to_email: str,
    teilnehmer_name: str,
    termin_title: str,
    termin_date: date,
    start_time: time,
    end_time: time,
    location: str,
) -> bool:
    """Verschickt eine kurze Anmeldebestätigung. Gibt True bei Erfolg zurück.

    Schlägt niemals mit einer Exception nach außen fehl (fehlende/fehlerhafte
    SMTP-Konfiguration darf die eigentliche Anmeldung nicht verhindern) – bei
    Problemen wird lediglich False zurückgegeben.
    """
    config = _smtp_config()
    if config is None:
        return False

    message = EmailMessage()
    message["Subject"] = f"Bestätigung: Anmeldung für {termin_title}"
    message["From"] = f"{config['from_name']} <{config['from_email']}>"
    message["To"] = to_email
    message.set_content(
        f"Hallo {teilnehmer_name},\n\n"
        f'deine Anmeldung für "{termin_title}" am {termin_date.strftime("%d.%m.%Y")} '
        f'({start_time.strftime("%H:%M")}–{end_time.strftime("%H:%M")} Uhr) in {location} '
        "ist bestätigt.\n\n"
        "Bei Fragen einfach melden – falls es weitere Infos gibt, bekommst du sie "
        "ebenfalls per E-Mail.\n\n"
        "Bis bald!"
    )

    try:
        with smtplib.SMTP(config["host"], config["port"], timeout=10) as smtp:
            smtp.starttls()
            smtp.login(config["user"], config["password"])
            smtp.send_message(message)
        return True
    except Exception:
        return False

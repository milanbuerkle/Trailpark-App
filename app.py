import streamlit as st

from db.database import init_db
from services.auth_service import ensure_admin_seeded
from utils.session import current_trainer, try_remember_login
from views import backup, kalender, login, meine_termine, set_password, termin_erstellen, trainer_verwalten

st.set_page_config(page_title="Trailpark App", page_icon="🚵", layout="wide")

init_db()
ensure_admin_seeded()

try_remember_login()

trainer = current_trainer()

kalender_page = st.Page(kalender.render, title="Kalender", icon="🗓️", default=True, url_path="kalender")
login_page = st.Page(login.render, title="Login", icon="🔑", url_path="login")
set_password_page = st.Page(set_password.render, title="Passwort festlegen", icon="🔒", url_path="passwort-festlegen")

if trainer is None:
    pages = [kalender_page, login_page]
elif trainer.must_set_password:
    pages = [set_password_page]
else:
    pages = [
        kalender_page,
        st.Page(termin_erstellen.render, title="Termin erstellen", icon="➕", url_path="termin-erstellen"),
        st.Page(meine_termine.render, title="Meine Termine", icon="📋", url_path="meine-termine"),
        st.Page(backup.render, title="Backup", icon="💾", url_path="backup"),
        login_page,
    ]
    if trainer.is_admin:
        pages.insert(
            4, st.Page(trainer_verwalten.render, title="Trainer verwalten", icon="🧑‍🤝‍🧑", url_path="trainer-verwalten")
        )

nav = st.navigation(pages)
nav.run()

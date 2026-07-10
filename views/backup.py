from datetime import date

import streamlit as st

from services.backup_service import (
    InvalidBackupFileError,
    export_csv_zip,
    export_db_bytes,
    restore_from_upload,
)
from utils.session import current_trainer


def render() -> None:
    st.title("Backup")

    trainer = current_trainer()
    if trainer is None:
        st.info("Bitte melde dich an, um ein Backup herunterzuladen.")
        return

    st.warning(
        "Auf Streamlit Community Cloud wird das Dateisystem bei jedem Redeploy "
        "zurückgesetzt. Ein Backup schützt die Daten nur, wenn es **vor** einem "
        "Redeploy heruntergeladen und **danach** wieder hochgeladen wird."
    )

    st.subheader("Backup herunterladen")
    st.download_button(
        "Datenbank herunterladen (.db)",
        data=export_db_bytes(),
        file_name=f"trailpark_backup_{date.today():%Y-%m-%d}.db",
        mime="application/octet-stream",
    )
    st.download_button(
        "Tabellen als CSV herunterladen (.zip)",
        data=export_csv_zip(),
        file_name=f"trailpark_backup_{date.today():%Y-%m-%d}.zip",
        mime="application/zip",
    )

    st.divider()
    st.subheader("Datenbank wiederherstellen")

    if not trainer.is_admin:
        st.info("Nur Admins können die Datenbank wiederherstellen.")
        return

    uploaded = st.file_uploader("SQLite-Backup (.db) hochladen", type=["db"])
    confirm = st.checkbox("Ich bestätige, dass die aktuelle Datenbank überschrieben wird.")

    if uploaded is not None and confirm:
        if st.button("Datenbank jetzt wiederherstellen"):
            try:
                safety_copy_path = restore_from_upload(uploaded.getvalue())
                st.success(
                    f"Datenbank wurde wiederhergestellt. Sicherheitskopie der vorherigen "
                    f"Datenbank: {safety_copy_path.name}"
                )
                st.rerun()
            except InvalidBackupFileError as exc:
                st.error(str(exc))

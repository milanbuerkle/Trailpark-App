# Trailpark App – Trainer-Terminplaner für den MTB-Verein

Streamlit-App, mit der Trainer sich für Kurstermine eintragen können. Der Kalender
mit allen Terminen ist für alle sichtbar (auch ohne Account) – ein Login wird nur
benötigt, um sich für einen Termin anzumelden oder selbst einen Termin anzulegen.

## Lokal starten

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
streamlit run app.py
```

Die App ist danach unter http://localhost:8501 erreichbar. Beim ersten Start wird
automatisch eine SQLite-Datenbank unter `data/trailpark.db` angelegt.

### Admin-Account einrichten

Der feste Admin-Account wird **nicht** im Quellcode hinterlegt, sondern über
Streamlit Secrets. Lege lokal eine Datei `.streamlit/secrets.toml` an
(git-ignoriert, wird nie committet):

```toml
admin_name = "Milan"
admin_email = "milan@example.com"
admin_password = "..."
```

Beim nächsten App-Start wird dieser Account automatisch angelegt (falls die
E-Mail noch nicht existiert). Für Streamlit Community Cloud die gleichen drei
Werte im "Secrets"-Bereich der App-Einstellungen hinterlegen.

### Bestätigungsmails einrichten (optional)

Wenn ein Termin "Name + E-Mail" bei der Teilnehmer-Anmeldung verlangt, kann die
App eine kurze Bestätigungsmail verschicken. Dazu in derselben
`.streamlit/secrets.toml` die SMTP-Zugangsdaten des Absender-Postfachs ergänzen:

```toml
smtp_host = "smtp.web.de"
smtp_port = 587
smtp_user = "deine@adresse.de"
smtp_password = "..."
smtp_from_email = "deine@adresse.de"
smtp_from_name = "MTB Verein"
```

Fehlt eine dieser Angaben (z.B. `smtp_password` leer), wird der Mailversand
einfach übersprungen – die Anmeldung selbst funktioniert trotzdem. Bei
Anbietern mit Zwei-Faktor-Authentifizierung (z.B. Gmail) wird meist ein
separates App-Passwort statt des normalen Passworts benötigt.

## Funktionen

- **Kalender** (Startseite): zeigt alle Termine, farbcodiert nach Belegung
  (🔴 kein Trainer angemeldet, 🟠 teilweise belegt, 🟢 voll besetzt). Sichtbar ohne Login.
- **Login**: geschlossenes Zugangsmodell – neue Accounts werden ausschließlich vom
  Admin über "Trainer verwalten" per Einmalpasswort angelegt (keine offene
  Selbstregistrierung). Beim ersten Login mit dem Einmalpasswort muss der Trainer
  ein eigenes Passwort festlegen. Jeder mit Account kann danach "Passwort ändern"
  nutzen. Der Login bleibt über einen Token in der URL erhalten ("angemeldet
  bleiben"), solange dieselbe URL (z.B. per Lesezeichen oder wiederhergestelltem
  Tab) erneut geöffnet wird. Bewusst kein Cookie-basiertes Verfahren: ein dafür
  probiertes Custom-Component brachte die Kalender-Komponente auf derselben
  Seite zum Verschwinden – `st.query_params` ist eine native Streamlit-Funktion
  ohne dieses Risiko.
- **Trainer verwalten** (nur Admin): neue Trainer einladen (Einmalpasswort wird
  einmalig angezeigt), Einmalpasswort bei Bedarf neu erzeugen.
- **Termin erstellen**: jeder eingeloggte Trainer kann einen neuen Termin anlegen.
  Trainer können sich für maximal 3 kommende Termine gleichzeitig anmelden, damit
  auch andere eine Chance bekommen.
- **Teilnehmer-Anmeldung**: im Termin-Dialog kann sich jeder (auch ohne Account)
  als Teilnehmer eintragen – reine Anwesenheitsliste ohne Kapazitätsgrenze.
  Beim Erstellen eines Termins legt man fest, ob nur der Name oder Name + E-Mail
  nötig ist (Standard: nur Name); bei E-Mail-Pflicht verschickt die App eine
  kurze Bestätigungsmail (siehe unten). Eingeloggte Trainer können Einträge
  wieder entfernen und sehen die hinterlegten E-Mail-Adressen.
- **Meine Termine**: Übersicht über selbst erstellte und eigene Anmeldungen.
  Selbst erstellte Termine können dort bearbeitet werden (nur durch den/die
  Ersteller/in).
- **Backup**: Download der Datenbank (jeder Trainer) bzw. Wiederherstellung (nur Admin).

## Deployment auf Streamlit Community Cloud

Wichtig: Streamlit Community Cloud setzt das Dateisystem bei **jedem Redeploy**
zurück – die lokale SQLite-Datenbank geht dabei verloren. Runbook:

1. Vor einem Redeploy (z.B. `git push`) im Backup-Bereich der laufenden App die
   Datenbank herunterladen.
2. Redeploy durchführen.
3. Direkt danach als Admin einloggen und die heruntergeladene `.db`-Datei im
   Backup-Bereich wieder hochladen und bestätigen.

Für echte, redeploy-sichere Persistenz später auf eine gehostete Datenbank
umsteigen (z.B. Turso/LibSQL) – dazu genügt es, `DATABASE_URL` in
`db/database.py` anzupassen, da die restliche App nur über `services/` auf die
Datenbank zugreift.

## Projektstruktur

```
app.py                  Einstiegspunkt (st.navigation)
db/                      SQLAlchemy-Modelle und Datenbankverbindung
services/                Geschäftslogik (Auth, Termine, Backup)
views/                   Streamlit-Seiten
utils/session.py         Login-Session-Helper
```

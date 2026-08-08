# VfB Stuttgart Kalender – automatischer Sync (Argentinien-Zeit)

Dieses kleine Projekt hält deinen Kalender automatisch aktuell, sobald DFL/UEFA
neue Anstoßzeiten für VfB-Stuttgart-Spiele veröffentlichen. Es läuft täglich
über GitHub Actions – du musst nichts manuell anstoßen.

## Wie es funktioniert

1. `update_calendar.py` fragt die kostenlose, öffentliche Fußball-API
   [OpenLigaDB](https://www.openligadb.de) ab (Bundesliga, DFB-Pokal,
   Champions League) und filtert alle VfB-Stuttgart-Spiele heraus.
2. Für jedes Spiel mit bereits bekannter Anstoßzeit wird ein Kalendereintrag
   erzeugt – automatisch von deutscher Zeit in argentinische Zeit umgerechnet
   (inkl. Sommerzeit-Handling für beide Länder).
3. Das Ergebnis wird als `vfb_2026_27.ics` gespeichert.
4. Ein GitHub-Actions-Workflow (`.github/workflows/update-ics.yml`) führt
   Schritt 1–3 **jeden Tag automatisch** aus und lädt die aktualisierte Datei
   ins Repository hoch – falls sich etwas geändert hat.
5. Dein Kalender (Google/Apple/Outlook) **abonniert** diese Datei über eine
   feste URL und holt sich Änderungen von selbst (i.d.R. alle paar Stunden,
   das steuert der jeweilige Kalender-Anbieter).

## Einmalige Einrichtung (ca. 2 Minuten – Repo und Dateien sind schon da)

Das Repository [`5hitcake/vfb-calendar`](https://github.com/5hitcake/vfb-calendar)
existiert bereits und enthält alle Dateien. Es bleiben nur noch zwei Schritte:

### 1. Schreibrechte für Actions aktivieren
- Im Repo: **Settings → Actions → General → Workflow permissions**
- Wähle **"Read and write permissions"** und speichere.
  (Ohne das darf der Workflow die aktualisierte `.ics`-Datei nicht zurück ins
  Repo committen.)

### 2. Ersten Lauf testen
- Im Repo: Tab **Actions → "VfB Stuttgart Kalender aktualisieren" → Run workflow**
- Nach ca. 1 Minute sollte eine `vfb_2026_27.ics`-Datei im Repo erscheinen
  bzw. aktualisiert werden.
- **Wichtig:** Öffne die Datei im Repo und prüfe, ob plausible Spiele mit
  Uhrzeiten drin stehen. Falls die Datei leer bleibt oder Fehler auftreten,
  sieh dir das Workflow-Log an (dort stehen `[WARN]`-Meldungen) – siehe
  "Bekannte Stolpersteine" unten.

### 3. Kalender abonnieren (nicht importieren!)
Die URL zur Rohdatei lautet:
```
https://raw.githubusercontent.com/5hitcake/vfb-calendar/main/vfb_2026_27.ics
```

**Google Calendar:**
Einstellungen → "Kalender hinzufügen" → "Von URL" → obige URL einfügen.

**Apple Kalender (iPhone/Mac):**
Einstellungen → Kalender → Account hinzufügen → "Andere" →
"Kalenderabo hinzufügen" → obige URL (am besten mit `webcal://` statt
`https://` am Anfang, dann öffnet es sich direkt in der Kalender-App).

**Outlook:**
Kalender hinzufügen → "Aus dem Internet" → obige URL.

Ab jetzt aktualisiert sich dein Kalender von selbst, sobald der tägliche
GitHub-Actions-Lauf neue Zeiten findet.

## Bekannte Stolpersteine

- **Champions League:** Der OpenLigaDB-Shortcut für die CL wechselt teils von
  Saison zu Saison (aktuell im Skript: `ucl2026`, testweise gesetzt). Falls im
  Log `0 VfB-Spiele gefunden` für die Champions League steht, sobald die
  Auslosung (27.08.2026) stattgefunden hat, in `update_calendar.py` in der
  Liste `COMPETITIONS` den Shortcut anpassen – am einfachsten testest du das
  mit Claude Code: "Ruf https://api.openligadb.de/getavailableleagues ab und
  finde den korrekten Shortcut für die Champions League 2026/27."
- **DFB-Pokal:** Erfahrungsgemäß bei OpenLigaDB manchmal verzögert gepflegt,
  besonders in frühen Runden mit Amateurvereinen. Falls ein Spiel fehlt, prüfe
  einfach kurz vfb.de zusätzlich.
- **Spiele ohne Uhrzeit:** Solange die DFL/UEFA einen Termin nur mit Datum
  (ohne Uhrzeit) führt, taucht das Spiel absichtlich noch nicht im Kalender
  auf – sobald OpenLigaDB die Uhrzeit nachträgt, erscheint es beim nächsten
  täglichen Lauf automatisch.

## Lokal testen (optional, z. B. mit Claude Code)

```bash
pip install -r requirements.txt
python update_calendar.py
cat vfb_2026_27.ics
```

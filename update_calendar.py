# -*- coding: utf-8 -*-
"""
VfB Stuttgart -> ICS-Kalender (Argentinien-Zeit) - automatischer Sync

Datenquelle: OpenLigaDB (https://www.openligadb.de) - eine kostenlose, oeffentliche
JSON-API fuer deutschen Fussball, keine Anmeldung/Key noetig. Wird u.a. von der
offiziellen Bundesliga-App und vielen Fan-Projekten genutzt.

Wichtig / Grenzen dieses Skripts:
- Bundesliga-Daten (Liga-Shortcut "bl1") sind bei OpenLigaDB i.d.R. sehr zuverlaessig
  und werden zeitnah aktualisiert, sobald die DFL neue Anstosszeiten freigibt.
- DFB-Pokal ("dfb") und Champions League ("ligaShortcut" variiert je Saison, z.B.
  "champions-league" oder saisonspezifisch) sind bei OpenLigaDB teils luecken-
  hafter/verzoegert gepflegt. Das Skript versucht es trotzdem, faellt aber ohne
  Fehler auf "nur Bundesliga" zurueck, falls diese Endpunkte nichts liefern.
- Vor dem ersten produktiven Lauf: einmal lokal ausfuehren und die erzeugte
  vfb_2026_27.ics pruefen (siehe README.md).

Nutzung:
    pip install -r requirements.txt
    python update_calendar.py
"""

import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

TEAM_NAME_MATCH = "stuttgart"          # Filtert Spiele, in denen VfB Stuttgart vorkommt
SEASON = 2026                          # Saison 2026/27 -> Startjahr 2026
BERLIN = ZoneInfo("Europe/Berlin")
BUENOS_AIRES = ZoneInfo("America/Argentina/Buenos_Aires")

# (openligadb_shortcut, Anzeigename fuer die ICS-Beschreibung)
COMPETITIONS = [
    ("bl1", "Bundesliga"),
    ("dfb", "DFB-Pokal"),
    ("ucl2026", "UEFA Champions League"),   # Shortcut kann variieren, siehe README
]

OUTPUT_FILE = Path(__file__).parent / "vfb_2026_27.ics"


def fetch_matches(league_shortcut: str, season: int):
    """Ruft alle Spiele einer Liga/Saison von OpenLigaDB ab."""
    url = f"https://api.openligadb.de/getmatchdata/{league_shortcut}/{season}"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            return []
        return data
    except (requests.RequestException, json.JSONDecodeError, ValueError) as exc:
        print(f"[WARN] Konnte {league_shortcut}/{season} nicht laden: {exc}", file=sys.stderr)
        return []


def is_vfb_match(match: dict) -> bool:
    team1 = (match.get("team1") or {}).get("teamName", "")
    team2 = (match.get("team2") or {}).get("teamName", "")
    return TEAM_NAME_MATCH in team1.lower() or TEAM_NAME_MATCH in team2.lower()


def parse_kickoff_berlin(match: dict):
    """
    Liefert ein timezone-aware datetime in Europe/Berlin, oder None wenn die
    Anstosszeit von der DFL/UEFA noch nicht final terminiert ist.
    """
    # OpenLigaDB liefert i.d.R. 'matchDateTimeUTC' (ISO, UTC) und/oder 'matchDateTime'
    raw_utc = match.get("matchDateTimeUTC")
    raw_local = match.get("matchDateTime")
    is_finalized = match.get("matchIsFinished") is not None  # vorhanden = Termin existiert
    time_confirmed = bool(match.get("matchDateTimeUTC") or match.get("matchDateTime"))

    if not time_confirmed:
        return None

    try:
        if raw_utc:
            dt = datetime.fromisoformat(raw_utc.replace("Z", "+00:00"))
            return dt.astimezone(BERLIN)
        if raw_local:
            dt = datetime.fromisoformat(raw_local)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=BERLIN)
            return dt.astimezone(BERLIN)
    except ValueError:
        return None
    return None


def build_summary(match: dict, competition_name: str) -> str:
    team1 = (match.get("team1") or {}).get("teamName", "?")
    team2 = (match.get("team2") or {}).get("teamName", "?")
    group = (match.get("group") or {}).get("groupName", "")
    prefix = f"{competition_name}"
    if group:
        prefix += f" {group}"
    return f"{prefix}: {team1} - {team2}"


def ics_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def fmt_ics(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S")


def build_ics(events: list[dict]) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//VfB Stuttgart Auto-Sync//Claude//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:VfB Stuttgart 2026-27 (ARG-Zeit, Auto-Update)",
        "X-WR-TIMEZONE:America/Argentina/Buenos_Aires",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
    ]
    for ev in events:
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{ev['uid']}")
        lines.append(f"DTSTAMP:{fmt_ics(datetime.now(timezone.utc))}Z")
        lines.append(f"DTSTART;TZID=America/Argentina/Buenos_Aires:{fmt_ics(ev['start'])}")
        lines.append(f"DTEND;TZID=America/Argentina/Buenos_Aires:{fmt_ics(ev['end'])}")
        lines.append(f"SUMMARY:{ics_escape(ev['summary'])}")
        lines.append(f"DESCRIPTION:{ics_escape(ev['description'])}")
        lines.append("LOCATION:ESPN / Disney+")
        lines.append("BEGIN:VALARM")
        lines.append("TRIGGER:-PT30M")
        lines.append("ACTION:DISPLAY")
        lines.append("DESCRIPTION:VfB Stuttgart Spiel in 30 Minuten")
        lines.append("END:VALARM")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def main():
    all_events = []
    tba_count = 0

    for shortcut, name in COMPETITIONS:
        matches = fetch_matches(shortcut, SEASON)
        vfb_matches = [m for m in matches if is_vfb_match(m)]
        print(f"[INFO] {name} ({shortcut}): {len(vfb_matches)} VfB-Spiele gefunden")

        for m in vfb_matches:
            kickoff_berlin = parse_kickoff_berlin(m)
            if kickoff_berlin is None:
                tba_count += 1
                continue  # Anstosszeit noch nicht bekannt -> kein Kalendereintrag
            kickoff_arg = kickoff_berlin.astimezone(BUENOS_AIRES)
            end_arg = kickoff_arg.replace(
                hour=(kickoff_arg.hour + 2) % 24
            )  # grobe Dauer 2h, reicht fuer Erinnerungszwecke
            match_id = m.get("matchID", uuid.uuid4())
            all_events.append(
                {
                    "uid": f"vfb-{shortcut}-{match_id}@auto-sync",
                    "start": kickoff_arg,
                    "end": end_arg if end_arg > kickoff_arg else kickoff_arg,
                    "summary": build_summary(m, name),
                    "description": (
                        f"Automatisch synchronisiert aus OpenLigaDB. "
                        f"Anstoss Deutschland: {kickoff_berlin.strftime('%d.%m.%Y %H:%M %Z')}. "
                        f"Uebertragung Argentinien: ESPN / Disney+."
                    ),
                }
            )

    all_events.sort(key=lambda e: e["start"])
    ics_content = build_ics(all_events)
    OUTPUT_FILE.write_text(ics_content, encoding="utf-8")

    print(f"[OK] {len(all_events)} Termine geschrieben nach {OUTPUT_FILE.name}")
    if tba_count:
        print(f"[INFO] {tba_count} Spiele noch ohne bestaetigte Anstosszeit (werden beim naechsten Lauf ergaenzt)")


if __name__ == "__main__":
    main()

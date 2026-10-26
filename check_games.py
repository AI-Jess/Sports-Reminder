"""Preview the daily women's college basketball reminder for any date.

Mirrors the iOS Shortcut's logic exactly, so a run here shows what the
Shortcut would send that day.

Usage:
    python check_games.py              # today
    python check_games.py 20260328     # a specific date (YYYYMMDD)
    python check_games.py 20260328 --debug   # also dump raw fields
"""

import json
import sys
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Same list as the Shortcut. Matched exactly against ESPN's team "location"
# field, wrapped in pipes so "USC" doesn't also match "USC Upstate".
MY_TEAMS = "|UConn|USC|South Carolina|"

# Any tournament game whose ESPN note contains one of these is included.
BIG_ROUNDS = ["Sweet 16", "Elite 8", "Elite Eight", "Final Four", "National Championship"]
TOURNEY_TAG = "Women's Basketball Championship"

URL = (
    "https://site.api.espn.com/apis/site/v2/sports/basketball/"
    "womens-college-basketball/scoreboard?dates={date}&groups=50&limit=300"
)
CENTRAL = ZoneInfo("America/Chicago")


def fetch(date: str) -> dict:
    req = urllib.request.Request(URL.format(date=date), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def build_message(data: dict, debug: bool = False) -> str:
    lines = []
    for event in data.get("events", []):
        comp = event["competitions"][0]
        teams = [c["team"].get("location", "") for c in comp["competitors"]]
        headline = (comp.get("notes") or [{}])[0].get("headline", "")
        tv = ", ".join(n for b in comp.get("broadcasts", []) for n in b.get("names", [])) or "TV TBD"

        if debug:
            print(f"  {teams} | note={headline!r} | tv={tv!r} | date={event['date']}")

        is_my_team = any(f"|{t}|" in MY_TEAMS for t in teams)
        round_name = next((r for r in BIG_ROUNDS if r in headline), None)
        is_big_round = TOURNEY_TAG in headline and round_name is not None

        if not (is_my_team or is_big_round):
            continue

        tip = datetime.fromisoformat(event["date"].replace("Z", "+00:00")).astimezone(CENTRAL)
        time_str = tip.strftime("%-I:%M %p CT")
        # ESPN lists the away team first; show "Away vs Home".
        matchup = " vs ".join(teams)
        prefix = f"🏆 {round_name}: " if is_big_round else ""
        lines.append(f"• {prefix}{matchup} — {time_str} · {tv}")

    if not lines:
        return ""
    return "🏀 Women's hoops today\n\n" + "\n".join(lines)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    debug = "--debug" in sys.argv
    date = args[0] if args else datetime.now(CENTRAL).strftime("%Y%m%d")
    data = fetch(date)
    print(f"Date {date}: {len(data.get('events', []))} games on ESPN")
    msg = build_message(data, debug)
    print("\n--- message ---")
    print(msg or "(nothing today — Shortcut stays silent)")


if __name__ == "__main__":
    main()

"""Daily women's college basketball reminder.

Checks ESPN, builds the message, posts it to Discord, and saves it for the
iPhone Shortcut to text to the group chat.

Usage:
    python check_games.py                      # today, preview only
    python check_games.py 20260328 --debug     # a past date, with raw fields
    python check_games.py --write --post       # what the daily job runs
"""

import json
import os
import sys
from pathlib import Path
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Edit this to change teams. Matched exactly against ESPN's short team name
# ("location"), wrapped in pipes so "USC" doesn't match "USC Upstate".
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
    games = []  # (tip-off time, line) so we can sort earliest first
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
        games.append((tip, f"• {prefix}{matchup} — {time_str} · {tv}"))

    if not games:
        return ""
    lines = [line for _, line in sorted(games)]
    return "🏀 Women's hoops today\n\n" + "\n".join(lines)


def post_to_discord(message: str, webhook: str) -> None:
    body = json.dumps({"content": message}).encode()
    req = urllib.request.Request(
        webhook,
        data=body,
        # Discord rejects requests without a real-looking User-Agent.
        headers={"Content-Type": "application/json", "User-Agent": "SportsReminder (github.com/AI-Jess/Sports-Reminder, 1.0)"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"Posted to Discord (HTTP {r.status})")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    debug = "--debug" in sys.argv
    date = args[0] if args else datetime.now(CENTRAL).strftime("%Y%m%d")
    data = fetch(date)
    print(f"Date {date}: {len(data.get('events', []))} games on ESPN")
    msg = build_message(data, debug)
    print("\n--- message ---")
    print(msg or "(nothing today — Shortcut stays silent)")

    # --write: save the message where the phone Shortcut picks it up.
    # The file is written even when empty, so the Shortcut knows the job ran.
    if "--write" in sys.argv:
        out = Path("out/days") / f"{date}.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(msg, encoding="utf-8")
        print(f"Wrote {out}")

    # --post: send to Discord (only if there's something to say).
    if "--post" in sys.argv and msg:
        webhook = os.environ.get("DISCORD_WEBHOOK", "")
        if webhook:
            post_to_discord(msg, webhook)
        else:
            print("DISCORD_WEBHOOK not set — skipped Discord")


if __name__ == "__main__":
    main()

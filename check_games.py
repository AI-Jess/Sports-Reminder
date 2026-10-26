"""Daily women's basketball reminder (college + WNBA).

Checks ESPN, builds one message, posts it to Discord, and saves it for the
iPhone Shortcut to text to the group chat. Teams and leagues live in
settings.json.

Usage:
    python check_games.py                          # today, preview only
    python check_games.py 20260328 20250921 --debug  # past dates, raw fields
    python check_games.py --write --post           # 9 AM job: Discord + phone text
    python check_games.py --pregame --post         # every 15 min: Discord before 1st game
    python check_games.py 20260403 --pregame --now=2026-04-03T17:52  # test pregame
"""

import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).parent
SETTINGS = json.loads((HERE / "settings.json").read_text(encoding="utf-8"))
CENTRAL = ZoneInfo("America/Chicago")
ESPN = "https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard?dates={date}"


def fetch(league: dict, date: str) -> dict:
    url = ESPN.format(path=league["espn_path"], date=date)
    if league.get("extra_params"):
        url += "&" + league["extra_params"]
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def team_names(team: dict) -> set:
    """Every name ESPN uses for a team, so settings can say 'LSU' or 'Indiana Fever'."""
    keys = ("location", "displayName", "shortDisplayName", "name", "abbreviation")
    return {team.get(k, "") for k in keys} - {""}


def short_name(team: dict, league: dict) -> str:
    # College: "UConn". WNBA: "Fever" reads better than "Indiana".
    if "wnba" in league["espn_path"]:
        return team.get("name") or team.get("displayName", "")
    return team.get("location") or team.get("displayName", "")


def tv_channels(comp: dict) -> list:
    """Keep it short: the first two channels, minus the always-there League Pass."""
    names = [n for b in comp.get("broadcasts", []) for n in b.get("names", [])]
    return [n for n in names if n != "WNBA League Pass"][:2]


def game_link(event: dict) -> str | None:
    """ESPN's page for this game. Tapping it opens the ESPN app (score, where to watch)."""
    for link in event.get("links", []):
        if "/game/" in link.get("href", ""):
            return link["href"]
    return None


def big_game_label(event: dict, comp: dict, rule: dict) -> str | None:
    """Return a round label if this game qualifies for everyone, else None."""
    headline = (comp.get("notes") or [{}])[0].get("headline", "")
    if rule.get("all_playoff_games"):
        if event.get("season", {}).get("type") == 3:  # ESPN: 3 = postseason
            return headline.removeprefix("WNBA ") or "Playoffs"
        return None
    if rule.get("note_contains") and rule["note_contains"] in headline:
        return next((r for r in rule.get("rounds", []) if r in headline), None)
    return None


def league_games(league: dict, data: dict, debug: bool) -> list:
    mine = set(league["my_teams"])
    rule = league.get("also_include", {})
    games = []
    for event in data.get("events", []):
        comp = event["competitions"][0]
        teams = [c["team"] for c in comp["competitors"]]
        tv = tv_channels(comp)
        label = big_game_label(event, comp, rule)
        is_mine = any(team_names(t) & mine for t in teams)

        if debug:
            note = (comp.get("notes") or [{}])[0].get("headline", "")
            print(f"  [{league['label']}] {[t.get('displayName') for t in teams]} | "
                  f"note={note!r} | season_type={event.get('season', {}).get('type')} | tv={tv!r} | "
                  f"links={[l.get('href') for l in event.get('links', [])][:2]}")

        if not (is_mine or label):
            continue
        tip = datetime.fromisoformat(event["date"].replace("Z", "+00:00")).astimezone(CENTRAL)
        games.append({
            "tip": tip,
            "prefix": f"🏆 {label}: " if label else "",
            "matchup": " vs ".join(short_name(t, league) for t in teams),
            "time": tip.strftime("%-I:%M %p") + " CT",
            "tv": ", ".join(tv) or "League Pass / TBD",
            "link": game_link(event),
        })
    return sorted(games, key=lambda g: g["tip"])


def render_game(g: dict, with_links: bool) -> str:
    # Discord: the matchup is the link; <> stops Discord adding a big preview card.
    matchup = f"[{g['matchup']}](<{g['link']}>)" if with_links and g["link"] else g["matchup"]
    return f"• {g['prefix']}{matchup} — {g['time']} · {g['tv']}"


def find_games(date: str, debug: bool = False) -> list:
    """[(league label, [games])] for leagues that have games that day."""
    found = [(lg["label"], league_games(lg, fetch(lg, date), debug)) for lg in SETTINGS["leagues"]]
    return [(label, games) for label, games in found if games]


def render(found: list, with_links: bool, title: str) -> str:
    sections = [f"{label}\n" + "\n".join(render_game(g, with_links) for g in games)
                for label, games in found]
    return title + "\n\n" + "\n\n".join(sections)


def post_to_discord(message: str) -> None:
    webhook = os.environ.get("DISCORD_WEBHOOK", "")
    if not webhook:
        print("DISCORD_WEBHOOK not set — skipped Discord")
        return
    req = urllib.request.Request(
        webhook,
        data=json.dumps({"content": message}).encode(),
        # Discord rejects requests without a real-looking User-Agent.
        headers={"Content-Type": "application/json",
                 "User-Agent": "SportsReminder (github.com/AI-Jess/Sports-Reminder, 1.0)"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"Posted to Discord (HTTP {r.status})")


def morning(date: str, found: list, write: bool, post: bool) -> None:
    """Morning: lineup to Discord (with links) and saved for the phone text (no links)."""
    out = HERE / "out" / "days" / f"{date}.txt"
    # The morning job is scheduled several times as a backup (GitHub sometimes
    # skips or delays scheduled runs). Only the first one that runs does anything.
    if "--once" in sys.argv and out.exists():
        print("Morning reminder already done today")
        return
    text = render(found, False, SETTINGS["title"]) if found else ""
    print(text or "(nothing today — stays silent)")
    if write:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")  # empty file = nothing today
    if post and found:
        post_to_discord(render(found, True, SETTINGS["title"]))


def pregame(date: str, found: list, now: datetime, post: bool) -> None:
    """Runs every ~15 min. Posts the linked lineup to Discord once a day,
    shortly before the first game. A marker file stops repeat posts."""
    marker = HERE / "out" / "days" / f"{date}.pregame"
    if not found:
        print("No games today")
        return
    if marker.exists():
        print("Pregame reminder already sent today")
        return
    first = min(g["tip"] for _, games in found for g in games)
    minutes = (first - now).total_seconds() / 60
    lead = SETTINGS.get("pregame_minutes_before", 10)
    # Checks run every 15 min and GitHub can start them late, so send as soon
    # as a check lands within lead+15 min of tip (or up to 15 min after it).
    if not (-15 <= minutes <= lead + 15):
        print(f"First game in {minutes:.0f} min — not time yet")
        return
    when = "now" if minutes <= 1 else f"in {minutes:.0f} min"
    msg = render(found, True, f"⏰ First game tips off {when}!")
    print(msg)
    if post:
        post_to_discord(msg)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(now.isoformat(), encoding="utf-8")
    print(f"Wrote {marker.name}")


def main():
    args = sys.argv[1:]
    debug, write, post = "--debug" in args, "--write" in args, "--post" in args
    # --now=2026-04-03T17:50 pretends it's that time (Central), for testing pregame.
    now_arg = next((a.split("=", 1)[1] for a in args if a.startswith("--now=")), None)
    now = datetime.fromisoformat(now_arg).replace(tzinfo=CENTRAL) if now_arg else datetime.now(CENTRAL)
    dates = [a for a in args if not a.startswith("--")] or [now.strftime("%Y%m%d")]
    for date in dates:
        print(f"=== {date}")
        found = find_games(date, debug)
        if "--pregame" in args:
            pregame(date, found, now, post)
        else:
            morning(date, found, write, post)
        print()


if __name__ == "__main__":
    main()

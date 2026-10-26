"""Daily women's basketball reminder (college + WNBA).

Checks ESPN, builds one message, posts it to Discord, and saves it for the
iPhone Shortcut to text to the group chat. Teams and leagues live in
settings.json.

Usage:
    python check_games.py                          # today, preview only
    python check_games.py 20260328 20250921 --debug  # past dates, raw fields
    python check_games.py --write --post           # what the daily job runs
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


def tv_channels(comp: dict) -> str:
    """Keep it short: the first two channels, minus the always-there League Pass."""
    names = [n for b in comp.get("broadcasts", []) for n in b.get("names", [])]
    return [n for n in names if n != "WNBA League Pass"][:2]


def watch_link(channel: str) -> str | None:
    """Short link to the app that streams this channel (from settings.json)."""
    for link, channels in SETTINGS.get("watch_links", {}).items():
        if channel in channels:
            return link
    return None


def render_tv(channels: list, for_discord: bool) -> str:
    if not channels:
        return "League Pass / TBD"
    if for_discord:
        # Masked links; <> stops Discord from adding a big preview card.
        return ", ".join(f"[{c}](<https://{watch_link(c)}>)" if watch_link(c) else c for c in channels)
    text = ", ".join(channels)
    link = next((watch_link(c) for c in channels if watch_link(c)), None)
    # Bare short link: iMessage turns it into a tappable link.
    return f"{text} ({link})" if link else text


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
        matchup = " vs ".join(short_name(t, league) for t in teams)
        prefix = f"🏆 {label}: " if label else ""
        games.append((tip, f"• {prefix}{matchup} — {tip.strftime('%-I:%M %p')} CT · ", tv))
    return sorted(games, key=lambda g: g[0])


def build_messages(date: str, debug: bool = False) -> tuple[str, str]:
    """Returns (text version, Discord version). Same content; Discord gets masked links."""
    found = [(lg["label"], league_games(lg, fetch(lg, date), debug)) for lg in SETTINGS["leagues"]]
    found = [(label, games) for label, games in found if games]
    if not found:
        return "", ""

    def render(for_discord: bool) -> str:
        sections = [
            f"{label}\n" + "\n".join(line + render_tv(tv, for_discord) for _, line, tv in games)
            for label, games in found
        ]
        return SETTINGS["title"] + "\n\n" + "\n\n".join(sections)

    return render(False), render(True)


def post_to_discord(message: str, webhook: str) -> None:
    req = urllib.request.Request(
        webhook,
        data=json.dumps({"content": message}).encode(),
        # Discord rejects requests without a real-looking User-Agent.
        headers={"Content-Type": "application/json",
                 "User-Agent": "SportsReminder (github.com/AI-Jess/Sports-Reminder, 1.0)"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"Posted to Discord (HTTP {r.status})")


def main():
    dates = [a for a in sys.argv[1:] if not a.startswith("--")] or [datetime.now(CENTRAL).strftime("%Y%m%d")]
    debug = "--debug" in sys.argv
    for date in dates:
        print(f"=== {date}")
        msg, discord_msg = build_messages(date, debug)
        print(msg or "(nothing today — stays silent)")
        if msg:
            print("\n[Discord version]\n" + discord_msg)

        # --write: save where the phone Shortcut picks it up (empty file = nothing today).
        if "--write" in sys.argv:
            out = HERE / "out" / "days" / f"{date}.txt"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(msg, encoding="utf-8")

        # --post: send to Discord, only if there's something to say.
        if "--post" in sys.argv and msg:
            webhook = os.environ.get("DISCORD_WEBHOOK", "")
            if webhook:
                post_to_discord(discord_msg, webhook)
            else:
                print("DISCORD_WEBHOOK not set — skipped Discord")
        print()


if __name__ == "__main__":
    main()

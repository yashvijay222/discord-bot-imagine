"""Post today's due reminders to the Discord bot channel.

Run once a day at 1 PM (via a Claude routine or any scheduler):
    DISCORD_TOKEN=... DISCORD_CHANNEL_ID=... python remind.py
    python remind.py --dry-run --any-hour   # print instead of posting, ignore the 1 PM check
    python remind.py --test             # run self-checks
"""
import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
CONFIG = Path(__file__).with_name("reminders.json")
DETROIT = ZoneInfo("America/Detroit")


def due(reminders, today: date):
    wd = WEEKDAYS[today.weekday()]
    return [r for r in reminders
            if r.get("weekday") == wd or r.get("day_of_month") == today.day]


def pick(reminders, rid, today: date):
    """The reminder with this id if it is due today, else None (so --send can't fire other reminders)."""
    return next((r for r in due(reminders, today) if r["id"] == rid), None)


def api(token, path, body=None):
    """Discord REST call: GET, or POST when there is a body. Raises on non-2xx."""
    req = urllib.request.Request(
        f"https://discord.com/api/v10/{path}",
        data=None if body is None else json.dumps(body).encode(),
        method="GET" if body is None else "POST",
        headers={"Authorization": f"Bot {token}", "Content-Type": "application/json",
                 "User-Agent": "ImagineBot (https://github.com, 1.0)"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or "null")


def post(token, channel_id, content, ping=()):
    """Post a message; only user IDs in `ping` get notified (never @everyone)."""
    api(token, f"channels/{channel_id}/messages",
        {"content": content, "allowed_mentions": {"users": list(ping)}})


def fetch_messages(token, channel_id, since: datetime):
    """Channel messages newest-first, paging back until older than `since` (max 1000)."""
    out, before = [], ""
    for _ in range(10):
        page = api(token, f"channels/{channel_id}/messages?limit=100{before}")
        out += page
        if len(page) < 100 or datetime.fromisoformat(page[-1]["timestamp"]) < since:
            break
        before = f"&before={page[-1]['id']}"
    return out


def render(messages, members, since: datetime):
    """Oldest-first '[date time] author: text' lines in Detroit time, without bots or old messages."""
    names = {uid: name for name, uid in members.items()}
    lines = []
    for m in sorted(messages, key=lambda m: m["timestamp"]):
        ts = datetime.fromisoformat(m["timestamp"])
        if m["author"].get("bot") or ts < since:  # the bot's own past reminders aren't evidence
            continue
        text = re.sub(r"<@!?(\d+)>", lambda x: "@" + names.get(x[1], x[1]), m["content"]) or "[attachment or embed]"
        lines.append(f"[{ts.astimezone(DETROIT):%Y-%m-%d %H:%M}] {m['author']['username']}: {text}")
    return "\n".join(lines) or "(no messages)"


def main():
    cfg = json.loads(CONFIG.read_text())
    now = datetime.now(ZoneInfo("America/Detroit"))
    # Scheduler fires at both 17:00 and 18:00 UTC (cron is UTC); only the one that is 1 PM in Michigan posts.
    if "--any-hour" not in sys.argv and now.hour != 13:
        print(f"{now:%H:%M} Detroit is not 1 PM, skipping")
        return
    today = now.date()
    todo = due(cfg["reminders"], today)
    dry = "--dry-run" in sys.argv
    if not dry:
        token, channel = os.environ["DISCORD_TOKEN"], os.environ["DISCORD_CHANNEL_ID"]
    for r in todo:
        user = cfg["members"][r["to"]]
        if dry:
            print(f"[{today}] @{r['to']} ({user}): {r['message']}")
        else:
            post(token, channel, f"<@{user}> {r['message']}", [user])
    print(f"{today}: {len(todo)} reminder(s) {'would be ' if dry else ''}sent")


def test():
    rs = json.loads(CONFIG.read_text())["reminders"]
    to = lambda d: sorted(r["to"] + "/" + (r.get("weekday") or "dom") for r in due(rs, d))
    assert to(date(2026, 11, 10)) == ["vincent/tue"]           # Tuesday
    assert to(date(2026, 11, 11)) == ["zlata/wed"]             # Wednesday
    assert to(date(2026, 11, 12)) == ["vincent/thu"]           # Thursday
    assert to(date(2026, 11, 14)) == []                        # Saturday
    assert to(date(2026, 12, 1)) == ["tappy/dom", "vincent/tue"]  # Dec 1 is a Tuesday
    assert pick(rs, "zlata-wed", date(2026, 11, 11))["to"] == "zlata"   # Wednesday
    assert pick(rs, "zlata-wed", date(2026, 11, 12)) is None            # not due Thursday
    assert pick(rs, "nope", date(2026, 11, 11)) is None
    assert all("id" in r for r in rs) and len({r["id"] for r in rs}) == len(rs)
    since = datetime(2026, 11, 1, tzinfo=ZoneInfo("UTC"))  # Nov 2026 18:00 UTC = 13:00 Detroit
    msgs = [
        {"timestamp": "2026-11-18T18:00:00+00:00", "author": {"username": "zlata"}, "content": "booked the room <@360012406015000577>"},
        {"timestamp": "2026-11-17T18:00:00+00:00", "author": {"username": "Imagine Bot", "bot": True}, "content": "Reminder: book"},
        {"timestamp": "2026-11-16T18:00:00+00:00", "author": {"username": "yash"}, "content": ""},
        {"timestamp": "2026-10-01T18:00:00+00:00", "author": {"username": "old"}, "content": "too old"},
    ]
    assert render(msgs, {"vincent": "360012406015000577"}, since) == (
        "[2026-11-16 13:00] yash: [attachment or embed]\n"
        "[2026-11-18 13:00] zlata: booked the room @vincent")
    assert render([], {}, since) == "(no messages)"
    print("ok")


if __name__ == "__main__":
    test() if "--test" in sys.argv else main()

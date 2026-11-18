"""Daily 1 PM reminders that skip tasks someone already said are done.

The Claude routine runs --check, decides which due tasks are already done, then --send's the rest:
    python3 remind.py --check          # today's due tasks + the read channel's last 21 days of messages
    python3 remind.py --send <id>      # post that reminder (only if it is due today)
    add --any-hour to either to skip the "only at 1 PM Detroit time" check (for testing)
    python3 remind.py --test           # self-checks
Needs DISCORD_TOKEN (and DISCORD_CHANNEL_ID for --send).
"""
import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta
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


def closed(now: datetime, args):
    """(message, exit code) when it isn't 1 PM in Detroit, else None. The routine fires at 17:00 and 18:00 UTC
    so one run is always 1 PM; the other exits 0. A --send outside 1 PM fails, so a late send isn't silently lost."""
    if "--any-hour" in args or now.hour == 13:
        return None
    if "--send" in args:
        return f"not sent: it is {now:%H:%M} in Detroit, past the 1 PM window", 1
    return f"{now:%H:%M} Detroit is not 1 PM, nothing to do", 0


def main():
    args = sys.argv[1:]
    if "--check" not in args and "--send" not in args:
        sys.exit(__doc__)
    cfg = json.loads(CONFIG.read_text())
    now = datetime.now(DETROIT)
    shut = closed(now, args)
    if shut:
        print(shut[0], file=sys.stderr if shut[1] else sys.stdout)
        sys.exit(shut[1])
    today = now.date()

    if "--send" in args:
        i = args.index("--send") + 1
        rid = args[i] if i < len(args) else ""
        r = pick(cfg["reminders"], rid, today)
        if r is None:
            sys.exit(f"not due today: {rid}")
        user = cfg["members"][r["to"]]
        post(os.environ["DISCORD_TOKEN"], os.environ["DISCORD_CHANNEL_ID"], f"<@{user}> {r['message']}", [user])
        print(f"sent {rid}")
        return

    todo = due(cfg["reminders"], today)
    print(f"Today: {today:%A %Y-%m-%d}")
    if not todo:
        print("Due today: none")
        return
    print("Due today:")
    for r in todo:
        print(f"- {r['id']}: @{r['to']}: {r['message']}")
    since = now - timedelta(days=21)
    print("\nMessages in the last 21 days:")
    print(render(fetch_messages(os.environ["DISCORD_TOKEN"], cfg["read_channel"], since), cfg["members"], since))


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
    two_pm, one_pm = datetime(2026, 11, 18, 14, 0, tzinfo=DETROIT), datetime(2026, 11, 18, 13, 59, tzinfo=DETROIT)
    assert closed(one_pm, ["--send", "zlata-wed"]) is None
    assert closed(two_pm, ["--send", "zlata-wed"])[1] == 1    # a late --send must fail loudly
    assert closed(two_pm, ["--check"])[1] == 0                # the routine's other hourly run is normal
    assert closed(two_pm, ["--send", "x", "--any-hour"]) is None
    print("ok")


if __name__ == "__main__":
    test() if "--test" in sys.argv else main()

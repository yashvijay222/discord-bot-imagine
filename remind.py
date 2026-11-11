"""Post today's due reminders to the Discord bot channel.

Run once a day at 1 PM (via a Claude routine or any scheduler):
    DISCORD_TOKEN=... DISCORD_CHANNEL_ID=... python remind.py
    python remind.py --dry-run --any-hour   # print instead of posting, ignore the 1 PM check
    python remind.py --test             # run self-checks
"""
import json
import os
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
CONFIG = Path(__file__).with_name("reminders.json")


def due(reminders, today: date):
    wd = WEEKDAYS[today.weekday()]
    return [r for r in reminders
            if r.get("weekday") == wd or r.get("day_of_month") == today.day]


def post(token, channel_id, user_id, message):
    body = json.dumps({
        "content": f"<@{user_id}> {message}",
        "allowed_mentions": {"users": [user_id]},
    }).encode()
    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{channel_id}/messages",
        data=body, method="POST",
        headers={"Authorization": f"Bot {token}", "Content-Type": "application/json",
                 "User-Agent": "ImagineBot (https://github.com, 1.0)"})
    urllib.request.urlopen(req).close()  # raises on non-2xx


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
            post(token, channel, user, r["message"])
    print(f"{today}: {len(todo)} reminder(s) {'would be ' if dry else ''}sent")


def test():
    rs = json.loads(CONFIG.read_text())["reminders"]
    to = lambda d: sorted(r["to"] + "/" + (r.get("weekday") or "dom") for r in due(rs, d))
    assert to(date(2026, 11, 10)) == ["vincent/tue"]           # Tuesday
    assert to(date(2026, 11, 11)) == ["zlata/wed"]             # Wednesday
    assert to(date(2026, 11, 12)) == ["vincent/thu"]           # Thursday
    assert to(date(2026, 11, 14)) == []                        # Saturday
    assert to(date(2026, 12, 1)) == ["tappy/dom", "vincent/tue"]  # Dec 1 is a Tuesday
    print("ok")


if __name__ == "__main__":
    test() if "--test" in sys.argv else main()

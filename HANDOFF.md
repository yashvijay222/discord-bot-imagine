# Handoff: Imagine Software Discord Bot

## Goal
One Discord bot for the Imagine Software club (MSU) that:
1. **Reminders** — every day at 1 PM Michigan time, @ board members in a bot channel when a task is due. *(built, working)*
2. **Calendar/messages** — not started, not yet specified.
3. **Call transcription + summaries** — not started; approach chosen, see below.

The club lead also wants the team to get comfortable with **Claude routines** (scheduled cloud agents) and **artifacts**.

## Repo
https://github.com/yashvijay222/discord-bot-imagine (branch `main`, latest commit `a5b4fdc`). Python 3, stdlib only, no dependencies.

- `reminders.json`: `members` maps names to Discord user IDs. `reminders` lists entries with a `weekday` (`mon`..`sun`) or a `day_of_month`, plus `to` and `message`.
- `remind.py`: posts today's due reminders through the Discord REST API (`POST /channels/{id}/messages`, with `allowed_mentions` set so the @ pings).
  - Reads the env vars `DISCORD_TOKEN` and `DISCORD_CHANNEL_ID`.
  - Posts only when it is 13:00 in America/Detroit, so a UTC cron that fires at both 17:00 and 18:00 handles daylight saving.
  - `python3 remind.py --test` runs the self-checks.
  - `--dry-run --any-hour` prints instead of posting and skips the hour check.
- `README.md` has the setup steps.

Current reminders:
| Who | When | Message |
|---|---|---|
| Vincent | Tuesday | Marketing post must be finished |
| Vincent | Thursday | Post the marketing material |
| Zlata | Wednesday | Book the Next Room + order food for the event |
| Tappy | 1st of month | Finalize all of this month's events |

## Current state
- The Discord app **"Imagine Bot"** (application/client ID `1570189702399533146`) was created under Yash's personal Discord account.
  - It's in a **private test server**, not the Imagine server yet.
  - Invite URL, which grants only View Channels + Send Messages: `https://discord.com/oauth2/authorize?client_id=1570189702399533146&scope=bot&permissions=3072`
- `reminders.json` currently holds **test user IDs** (Yash and one other test member), not the real board members.
  - The test channel ID is `1050054223695446078`.
- A live test post succeeded on 2026-11-11.
- **The bot token was exposed in a chat and must be reset** (Developer Portal → Bot → Reset Token). It was never committed. Never commit it or paste it in chat.

## Next steps
1. **Decide who owns the bot.** It may be better to recreate it under a club-owned Discord account, or add club members to the app's Team, so it isn't tied to Yash.
2. **Daily routine (not created yet).** It's blocked on:
   - GitHub connected to the Claude account (claude.ai/connect-github).
   - `DISCORD_TOKEN` and `DISCORD_CHANNEL_ID` set as env vars in the cloud environment.

   Then create a routine on this repo with:
   - cron `0 17,18 * * *` (UTC)
   - a small model (Sonnet)
   - prompt: `Run "python3 remind.py" from the repo root and report its output. Do not modify any files.`

   Run it once to verify.
3. **Move to the Imagine server.**
   - Someone with Manage Server opens the invite URL above.
   - Create a `#bot` channel.
   - Replace the IDs in `reminders.json` with Vincent's, Zlata's and Tappy's real Discord user IDs (Developer Mode → right-click → Copy User ID).
   - Update `DISCORD_CHANNEL_ID`.

## Transcription plan (agreed direction, not built)
**Option A (chosen to start):**
- Record meetings with the existing **Craig** bot (free, records each speaker on a separate track).
- Then run a local script, `summarize.py <recording>`, that:
  1. Transcribes with Whisper locally (e.g. faster-whisper).
  2. Summarizes with the Claude API (summary, decisions, action items with owners).
  3. Posts the result to the bot channel, reusing `post()` from `remind.py`.
- No hosting needed. Needs a Claude API key.

**Option B (later, if the manual step gets annoying):**
- The bot joins voice itself (`/record`, `/stop`) and posts automatically.
- Needs an always-on host (~$5/mo), most likely discord.js.
- Needs support for Discord's voice end-to-end encryption (DAVE) to capture audio.

**Either way:** announce recording and get consent at the start of each meeting.

## Working preferences
Keep it minimal: stdlib first, no speculative abstractions. Leave one runnable self-check for any non-trivial logic.

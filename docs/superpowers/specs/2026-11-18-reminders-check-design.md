# Reminders that skip tasks already done

## Why
Reminders go out even when the task is already done (e.g. Zlata already said she booked the room).
Yash wants the bot to check a channel first, with everything running as Claude routines and
editable from claude.ai in the browser, no laptop needed.

## Goals / non-goals / anti-goals
- Goal: before each 1 PM reminder, Claude reads the channel and skips tasks someone has said are done.
- Goal: Yash steers it by editing plain files on GitHub (`context.md`, `reminders.json`).
- Non-goal: tracking tasks, replying in the channel, or changing what reminders say.
- Anti-goal: the bot posting anything other than the fixed reminder text, whatever the channel says.

## Decisions (Yash)
- Anyone saying in the channel, in any wording, that a task is done counts. The channel is trusted.
- Tasks are sometimes done early, so Claude must judge which event a message is about, not just its date.
- Event dates and other context live in a `context.md` file Yash edits as needed; the routine reads it each run.
- Approach: Claude judges, the script posts.

## Approaches considered
1. **Claude judges, the script posts (picked).** `remind.py --check` prints due tasks and recent messages;
   Claude decides send/skip; `remind.py --send <id>` posts the fixed text. Output stays predictable; code stays testable.
2. Claude does everything with curl. Less code, but Claude writes every post, so channel text could steer what the bot says.

## Design
- `reminders.json`: each reminder gets an `id` (e.g. `zlata-wed`); new top-level `read_channel` = the channel ID to read.
- `context.md` (new, plain English): upcoming events with dates, what "done" means per task, any notes.
- `remind.py --check`: if it is 1 PM in Detroit (or `--any-hour`), prints today's date, the due tasks
  (id, who, text), and the read channel's messages from the last 21 days as `[date time] author: text`.
- `remind.py --send <id>`: posts that reminder (fixed text + @mention), and refuses any id not due today
  or outside 1 PM, so Claude can't trigger other reminders.
- Routine prompt: read `context.md`, run `--check`, for each due task decide whether a message clearly says it is
  done *for the upcoming event*; run `--send <id>` for the rest; when unsure, or `context.md` has no upcoming
  event, send. Report every decision with the quoted message that justified a skip. Don't modify files.
- The plain `remind.py` (send everything due) and `--dry-run` go away; `--check` is the dry run.
- Self-check (`--test`) covers due-date logic, the 21-day message window, and the `--send` guard.

## Setup Yash does
- Discord Developer Portal → Bot → turn on **Message Content Intent**.
- Re-invite the bot with Read Message History added (permissions `68608`), or grant it on the channel.
- Fill in `context.md` and `read_channel`.

## Left to the builder
- How `--check` paginates Discord history (100 per request) and caps it.
- Rendering `<@id>` mentions in messages as names.

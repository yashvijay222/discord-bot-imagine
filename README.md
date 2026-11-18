# Imagine Software Discord Bot

Phase 1: daily 1 PM (Michigan time) reminders that @ board members in a bot channel.
Phase 2: meeting summaries from Craig recordings (`summarize.py`, run locally).
Later: calendar.

- `reminders.json` — who gets reminded, when, and what it says. Edit this to add reminders.
- `remind.py` — posts today's reminders. No dependencies (Python 3.9+ stdlib).

```bash
python3 remind.py --test                  # self-checks
python3 remind.py --dry-run --any-hour    # show what today would send
```

## One-time setup

### 1. Create the bot (Discord Developer Portal)
1. https://discord.com/developers/applications → **New Application** → name it "Imagine Bot".
2. **Bot** tab → **Reset Token** → copy it. This is `DISCORD_TOKEN`. Never commit it.
3. **OAuth2 → URL Generator**: scope `bot`; permissions `View Channels`, `Send Messages`.
   Open the generated URL and add the bot to the Imagine server (needs Manage Server on the server).

### 2. Set up the channel and IDs
1. Discord → User Settings → Advanced → turn on **Developer Mode**.
2. Create a `#bot` channel. Right-click it → **Copy Channel ID**. This is `DISCORD_CHANNEL_ID`.
3. Right-click Vincent, Zlata, Tappy → **Copy User ID** → paste into `members` in `reminders.json`.

### 3. Test from your laptop
```bash
DISCORD_TOKEN=xxx DISCORD_CHANNEL_ID=123 python3 remind.py --any-hour
```

### 4. Schedule it (Claude routine)
1. Connect GitHub to Claude: https://claude.ai/connect-github
2. At https://claude.ai/code, open the **Default** cloud environment settings and add env vars
   `DISCORD_TOKEN` and `DISCORD_CHANNEL_ID`.
3. Create a routine on this repo, cron `0 17,18 * * *` (UTC; the script posts only on the run that is 1 PM in Michigan),
   prompt: `Run "python3 remind.py" from the repo root and report its output. Do not modify any files.`

## Meeting summaries (`summarize.py`)

1. Announce the recording and get consent, then record the call with the [Craig](https://craig.chat) bot.
2. Download the multi-track **FLAC zip** from Craig (one track per speaker).
3. Run it (first run downloads the Whisper model):
```bash
pip install faster-whisper anthropic
export ANTHROPIC_API_KEY=... DISCORD_TOKEN=... DISCORD_CHANNEL_ID=...
python3 summarize.py craig-recording.zip --dry-run   # check the summary first
python3 summarize.py craig-recording.zip             # post it to the bot channel
```
Transcription runs locally with faster-whisper (`WHISPER_MODEL=medium` for better accuracy); only the text goes to Claude.
The full transcript is saved as `craig-recording.transcript.txt`.

"""Transcribe a Craig recording locally and post a meeting summary to the Discord bot channel.

    python3 summarize.py craig-recording.zip            # Craig's multi-track zip (one track per speaker)
    python3 summarize.py alice.flac bob.flac            # or individual tracks
    python3 summarize.py craig-recording.zip --dry-run  # print the summary instead of posting
    python3 summarize.py --test                         # self-checks

Needs: pip install faster-whisper anthropic, plus ANTHROPIC_API_KEY, DISCORD_TOKEN, DISCORD_CHANNEL_ID.
The full transcript is saved next to the first input as <name>.transcript.txt.
"""
import os
import re
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path

from remind import post

AUDIO = {".flac", ".ogg", ".opus", ".m4a", ".mp3", ".wav", ".aac", ".aiff"}
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")  # "medium"/"large-v3" = better but slower
PROMPT = """You summarize club meeting transcripts for Imagine Software, a student software club at MSU.
The transcript lines are "[mm:ss] speaker: text". Reply in Discord markdown with exactly these sections:

**Summary** - 3-6 bullets on what was discussed.
**Decisions** - bullets, or "None" if nothing was decided.
**Action items** - one bullet per task: "owner - task (due date if one was said)". Use the speaker names as given; write "unassigned" if nobody took it.

Only include what was actually said. Keep it under 1500 characters if you can."""


def speaker(path):
    return re.sub(r"^\d+-", "", Path(path).stem)  # Craig names tracks "1-username.flac"


def merge(tracks):
    """{speaker: [(start_seconds, text)]} -> one transcript ordered by time."""
    lines = sorted((start, who, text) for who, segs in tracks.items() for start, text in segs)
    return "\n".join(f"[{int(s) // 60:02d}:{int(s) % 60:02d}] {who}: {t.strip()}" for s, who, t in lines)


def chunks(text, limit=2000):
    """Split into Discord-sized messages, on line breaks when possible."""
    out = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        cut = cut if cut > 0 else limit
        out.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return out + [text] if text else out


def audio_files(args, tmp):
    files = []
    for a in map(Path, args):
        if a.suffix == ".zip":
            with zipfile.ZipFile(a) as z:
                z.extractall(tmp)
            files += sorted(p for p in Path(tmp).rglob("*") if p.suffix.lower() in AUDIO)
        else:
            files.append(a)
    return files


def transcribe(files):
    from faster_whisper import WhisperModel
    model = WhisperModel(WHISPER_MODEL, compute_type="int8")
    tracks = {}
    for f in files:
        print(f"transcribing {f.name}...", file=sys.stderr)
        segments, _ = model.transcribe(str(f), vad_filter=True)  # VAD skips Craig's silent padding
        tracks[speaker(f)] = [(s.start, s.text) for s in segments]
    return tracks


def summarize(transcript):
    import anthropic
    r = anthropic.Anthropic().beta.messages.create(
        model="claude-opus-5-5", max_tokens=16000, system=PROMPT,
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",  # retry on another model if declined
        messages=[{"role": "user", "content": transcript}])
    if r.stop_reason == "refusal":
        sys.exit("Claude declined to summarize this transcript.")
    return "".join(b.text for b in r.content if b.type == "text")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    with tempfile.TemporaryDirectory() as tmp:
        files = audio_files(args, tmp)
        if not files:
            sys.exit("no audio files found")
        transcript = merge(transcribe(files))
    out = Path(args[0]).with_suffix(".transcript.txt")
    out.write_text(transcript)
    print(f"transcript saved to {out}", file=sys.stderr)
    message = f"**Meeting summary - {date.today()}**\n\n{summarize(transcript)}"
    if "--dry-run" in sys.argv:
        print(message)
        return
    token, channel = os.environ["DISCORD_TOKEN"], os.environ["DISCORD_CHANNEL_ID"]
    for part in chunks(message):
        post(token, channel, part)
    print("posted")


def test():
    assert speaker("rec/1-yash.flac") == "yash" and speaker("zlata.ogg") == "zlata"
    t = merge({"yash": [(65.2, " hi "), (0, "start")], "zlata": [(30, "yo")]})
    assert t == "[00:00] yash: start\n[00:30] zlata: yo\n[01:05] yash: hi", t
    assert chunks("") == [] and chunks("short") == ["short"]
    assert chunks("aaa\nbbb\nccc", limit=8) == ["aaa\nbbb", "ccc"]
    assert chunks("x" * 5, limit=2) == ["xx", "xx", "x"]  # no newline: hard cut
    assert all(len(c) <= 2000 for c in chunks(("word " * 30 + "\n") * 100))
    print("ok")


if __name__ == "__main__":
    test() if "--test" in sys.argv else main()

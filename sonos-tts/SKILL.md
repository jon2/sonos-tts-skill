---
name: sonos-tts
description: Generate text-to-speech audio and play it on Sonos speakers. Use when the user wants spoken announcements, voice playback of short messages, or reusable TTS support through local Sonos rooms or room groups. Especially relevant for requests like "say this on Office," "announce this over Sonos," "announce to the outdoor zone," "create a house speaker announcement," or when setting up reusable spoken alert workflows.
---

# Sonos TTS

Use `scripts/announce.py` for the normal human-friendly path. It wraps `scripts/sonos_tts.py`, resolves one or more target rooms, and by default attempts a best-effort restore of prior playback and grouping after the announcement finishes.

## Quick workflow

1. Read local speaker names from `/home/jon/.openclaw/workspace/TOOLS.md` when working in Jon's environment.
2. For a one-room announcement, run:

```bash
python3 /home/jon/.openclaw/workspace/skills/sonos-tts/scripts/announce.py --room "Office" "Your message here"
```

3. For multiple rooms, run:

```bash
python3 /home/jon/.openclaw/workspace/skills/sonos-tts/scripts/announce.py --rooms "Office,Main Level" "Meeting starts in five minutes"
```

4. For direct low-level access or URL generation only, use `scripts/sonos_tts.py`.

## Guidance

- Keep messages short. Sonos announcements work best when they are brief and clear.
- Use exact Sonos room names unless a local zone alias is configured.
- The script starts or reuses a small HTTP server that serves files from `tts-cache/`.
- Generated files are cached in `/home/jon/.openclaw/workspace/tts-cache/`.
- By default the script snapshots current Sonos state and attempts a best-effort restore after the announcement.
- By default the wrapper also uses ducked announcement volume when a room is already playing.
- Use `--volume` to force an absolute announcement volume.
- Use `--duck <n>` to reduce current playing volume by `n` steps for the announcement.
- Use `--no-restore` if you want the announcement to replace current playback instead.

## Common examples

### Speak on one room

```bash
python3 /home/jon/.openclaw/workspace/skills/sonos-tts/scripts/announce.py --room "Office" "Hey Jon, this is Jeeves."
```

### Speak on more than one room

```bash
python3 /home/jon/.openclaw/workspace/skills/sonos-tts/scripts/announce.py --rooms "Office,Main Level" "Dinner is ready."
```

### Use a named zone from config

```bash
python3 /home/jon/.openclaw/workspace/skills/sonos-tts/scripts/announce.py --zone outdoor "Come inside."
```

### Force louder volume

```bash
python3 /home/jon/.openclaw/workspace/skills/sonos-tts/scripts/announce.py --room "Main Level" --volume 45 "Dinner is ready."
```

### Replace playback without restoring it

```bash
python3 /home/jon/.openclaw/workspace/skills/sonos-tts/scripts/announce.py --room "Office" --no-restore "This will leave the announcement loaded on the speaker."
```

### Generate speech without playback

```bash
python3 /home/jon/.openclaw/workspace/skills/sonos-tts/scripts/sonos_tts.py --print-url "Test message"
```

## Local zone aliases

`announce.py` can read a JSON config file from `~/.config/sonos-tts/config.json`.

Example:

```json
{
  "zones": {
    "outdoor": ["Pool", "Pavilion"],
    "downstairs": ["Office", "Main Level"]
  }
}
```

## Troubleshooting

Read `references/setup-notes.md` when playback fails, `gTTS` is missing, the generated URL is not reachable, or restore behavior is imperfect.

---
name: sonos-tts
description: Generate text-to-speech audio and play it on Sonos speakers. Use when the user wants spoken announcements, voice playback of short messages, or reusable TTS support through local Sonos rooms or room groups. Supports configurable TTS backends, including gTTS today and ElevenLabs integration for more flexible voices.
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

4. For ElevenLabs, either set it in config or pass backend/voice on the command line:

```bash
python3 /home/jon/.openclaw/workspace/skills/sonos-tts/scripts/announce.py --room "Office" --backend elevenlabs --voice "VOICE_ID" "Testing a different voice"
```

5. For direct low-level access or URL generation only, use `scripts/sonos_tts.py`.

## Guidance

- Keep messages short. Sonos announcements work best when they are brief and clear.
- Use exact Sonos room names unless a local zone alias is configured.
- The script starts or reuses a small HTTP server that serves files from `tts-cache/`.
- Generated files are cached in `/home/jon/.openclaw/workspace/tts-cache/`.
- By default the script snapshots current Sonos state and attempts a best-effort restore after the announcement.
- For multi-room announcements, the script temporarily groups targets under one coordinator and plays the announcement once for tighter sync.
- By default the wrapper also uses ducked announcement volume when a room is already playing.
- Use `--volume` to force an absolute announcement volume.
- Use `--duck <n>` to reduce current playing volume by `n` steps for the announcement.
- Use `--backend gtts|elevenlabs` to select a speech engine.
- Use `--voice` for backend-specific voice selection.
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

### Use ElevenLabs for a more expressive voice

```bash
python3 /home/jon/.openclaw/workspace/skills/sonos-tts/scripts/announce.py --room "Office" --backend elevenlabs --voice "VOICE_ID" "All right, listen up."
```

### Replace playback without restoring it

```bash
python3 /home/jon/.openclaw/workspace/skills/sonos-tts/scripts/announce.py --room "Office" --no-restore "This will leave the announcement loaded on the speaker."
```

### Generate speech without playback

```bash
python3 /home/jon/.openclaw/workspace/skills/sonos-tts/scripts/sonos_tts.py --print-url "Test message"
```

## Local config

`announce.py` and `sonos_tts.py` can read a JSON config file from `~/.config/sonos-tts/config.json`.

Read `references/setup-notes.md` for backend configuration details, especially ElevenLabs API key and voice setup.

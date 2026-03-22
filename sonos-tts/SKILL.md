---
name: sonos-tts
description: Generate text-to-speech audio and play it on Sonos speakers. Use when the user wants spoken announcements, voice playback of short messages, or reusable TTS support through local Sonos rooms. Especially relevant for requests like "say this on Office," "announce this over Sonos," "create a house speaker announcement," or when setting up recurring spoken alerts.
---

# Sonos TTS

Use `scripts/sonos_tts.py` to turn text into an MP3, serve it over HTTP on the local network, and optionally play it on a Sonos speaker.

## Quick workflow

1. Read `/home/jon/.openclaw/workspace/TOOLS.md` if you need local speaker names.
2. For direct playback, run:

```bash
python3 /home/jon/.openclaw/workspace/skills/sonos-tts/scripts/sonos_tts.py --sonos "Office" --volume 35 "Your message here"
```

3. For URL generation only, run:

```bash
python3 /home/jon/.openclaw/workspace/skills/sonos-tts/scripts/sonos_tts.py --print-url "Your message here"
```

## Guidance

- Keep messages short. Sonos announcements work best when they are brief and clear.
- Set `--volume` when audibility matters.
- Use exact Sonos room names.
- The script starts or reuses a small HTTP server that serves files from `tts-cache/`.
- Generated files are cached in `/home/jon/.openclaw/workspace/tts-cache/`.

## Common examples

### Speak on one room

```bash
python3 /home/jon/.openclaw/workspace/skills/sonos-tts/scripts/sonos_tts.py --sonos "Office" "Hey Jon, this is Jeeves."
```

### Speak louder

```bash
python3 /home/jon/.openclaw/workspace/skills/sonos-tts/scripts/sonos_tts.py --sonos "Main Level" --volume 45 "Dinner is ready."
```

### Generate speech without playback

```bash
python3 /home/jon/.openclaw/workspace/skills/sonos-tts/scripts/sonos_tts.py --print-url "Test message"
```

## Troubleshooting

Read `references/setup-notes.md` when playback fails, `gTTS` is missing, or the generated URL is not reachable.

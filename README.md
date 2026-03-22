# sonos-tts-skill

OpenClaw skill for generating text-to-speech audio and playing it on Sonos speakers.

## Contents

- `sonos-tts/` — the skill folder
- `sonos-tts.skill` — packaged skill artifact

## Requirements

- `sonos` CLI
- Python 3
- `gtts` Python package
- A machine on the same LAN as the Sonos speakers

## Friendly wrapper

Use the wrapper for normal announcements:

```bash
python3 sonos-tts/scripts/announce.py --room "Office" "Hello from Jeeves"
```

Multiple rooms:

```bash
python3 sonos-tts/scripts/announce.py --rooms "Office,Main Level" "Dinner is ready"
```

Named zone from config:

```bash
python3 sonos-tts/scripts/announce.py --zone outdoor "Come inside"
```

## Notes

- Best-effort restore of prior playback and grouping is enabled by default
- Announcement volume can be ducked relative to current playback
- `sonos_tts.py` remains available for lower-level direct use

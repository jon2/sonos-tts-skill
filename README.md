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

## Usage

The main script is:

```bash
python3 sonos-tts/scripts/sonos_tts.py --sonos "Office" --volume 35 "Hello from Jeeves"
```

Generate a URL without playing it:

```bash
python3 sonos-tts/scripts/sonos_tts.py --print-url "Test message"
```

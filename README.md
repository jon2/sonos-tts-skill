# sonos-tts-skill

OpenClaw skill for generating text-to-speech audio and playing it on Sonos speakers.

## Features

- Sonos room and multi-room announcements
- Synchronized group playback for multi-speaker announcements
- Best-effort restore of prior grouping and playback state
- Configurable TTS backends (`gtts` and `elevenlabs`)

## Friendly wrapper

```bash
python3 sonos-tts/scripts/announce.py --room "Office" "Hello from Jeeves"
```

Use ElevenLabs:

```bash
python3 sonos-tts/scripts/announce.py --room "Office" --backend elevenlabs --voice "VOICE_ID" "Testing a different voice"
```

# Sonos TTS Setup Notes

## Requirements

- `sonos` CLI installed and able to reach local speakers
- Python with `gtts` importable
- Sonos speakers able to fetch HTTP URLs from the machine running OpenClaw

## Local Environment Notes

- Speaker names and IPs may be stored in `/home/jon/.openclaw/workspace/TOOLS.md`
- Generated audio is served from `/home/jon/.openclaw/workspace/tts-cache/`
- Default HTTP port is `8765`

## Troubleshooting

### Sonos does not play audio

Check these, in order:
- Confirm the room name matches exactly
- Confirm the generated URL works with `curl -I <url>`
- Confirm the local IP is reachable from the Sonos subnet
- If playback starts but cuts out, retry after a second generation

### `Failed to import gTTS`

Install it with pip if needed. In this environment that was:

```bash
pip3 install --break-system-packages gtts
```

### The HTTP server is stale or wedged

Remove the pid file from `tts-cache/http-server.pid` and rerun the script.

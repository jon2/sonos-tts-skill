# Sonos TTS Setup Notes

## Requirements

- `sonos` CLI installed and able to reach local speakers
- Python with `requests` and either `gtts` or an enabled backend configuration
- Sonos speakers able to fetch HTTP URLs from the machine running OpenClaw

## Local Environment Notes

- Speaker names and IPs may be stored in `/home/jon/.openclaw/workspace/TOOLS.md`
- Generated audio is served from `/home/jon/.openclaw/workspace/tts-cache/`
- Default HTTP port is `8765`
- Optional local zone aliases and TTS settings can live in `~/.config/sonos-tts/config.json`

## Config Structure

Example config:

```json
{
  "zones": {
    "outdoor": ["Pool", "Pavilion"],
    "downstairs": ["Office", "Main Level"]
  },
  "tts": {
    "backend": "gtts",
    "elevenlabs": {
      "voiceId": "YOUR_VOICE_ID",
      "modelId": "eleven_multilingual_v2"
    }
  }
}
```

## ElevenLabs Setup

You can configure ElevenLabs in either of these ways:
- Set `ELEVENLABS_API_KEY` in the environment
- Add `tts.elevenlabs.apiKey` to the config file

Then either:
- set `tts.backend` to `elevenlabs` in config, or
- pass `--backend elevenlabs` on the command line

You can choose a voice by:
- passing `--voice <voice-id>`
- or setting `tts.elevenlabs.voiceId` in config

## Troubleshooting

### ElevenLabs backend selected but it fails

Check these, in order:
- Confirm `ELEVENLABS_API_KEY` is set or `apiKey` is present in config
- Confirm the voice ID exists in your ElevenLabs account
- Confirm outbound HTTPS access works from this machine
- Check the API error text returned by the script

### Sonos does not play audio

Check these, in order:
- Confirm the room name matches exactly
- Confirm the generated URL works with `curl -I <url>`
- Confirm the local IP is reachable from the Sonos subnet
- If playback starts but cuts out, retry after a second generation

### Restore did not return the speaker to exactly the prior state

The restore logic is best-effort. It snapshots current track URI, transport state, volume, and group membership, then reapplies them after the announcement.

Limitations:
- It may not restore exact queue position or elapsed playback time
- Some Sonos sources may resume imperfectly depending on URI type
- Playback is only auto-restored for rooms/groups that were actively `PLAYING` when the announcement began
- If a room or group was `PAUSED` or `STOPPED` before the announcement, the script restores topology/volume only and leaves playback off to avoid reviving stale URIs
- Group restoration depends on visible speakers and successful join/unjoin operations
- The current ducking behavior lowers announcement volume relative to active playback; it does not mix TTS over existing audio
- Multi-room announcements are synchronized by temporarily regrouping targets under a single coordinator before playback

### `Failed to import gTTS`

Install it with pip if needed. In this environment that was:

```bash
pip3 install --break-system-packages gtts
```

### The HTTP server is stale or wedged

Remove the pid file from `tts-cache/http-server.pid` and rerun the script.

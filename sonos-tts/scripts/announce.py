#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SONOS_TTS = SCRIPT_DIR / 'sonos_tts.py'
DEFAULT_CONFIG = Path.home() / '.config' / 'sonos-tts' / 'config.json'


def load_config(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def resolve_targets(args, config: dict) -> list[str]:
    rooms: list[str] = []
    if args.room:
        rooms.extend(args.room)
    if args.rooms:
        for item in args.rooms:
            rooms.extend([part.strip() for part in item.split(',') if part.strip()])
    if args.zone:
        zones = config.get('zones', {})
        for zone in args.zone:
            members = zones.get(zone)
            if not members:
                raise SystemExit(f'Unknown zone: {zone}. Add it to {args.config}.')
            rooms.extend(members)
    deduped: list[str] = []
    seen = set()
    for room in rooms:
        if room not in seen:
            deduped.append(room)
            seen.add(room)
    if not deduped:
        raise SystemExit('No target rooms specified. Use --room, --rooms, or --zone.')
    return deduped


def main():
    parser = argparse.ArgumentParser(description='Friendly wrapper for Sonos TTS announcements')
    parser.add_argument('text', help='Text to announce')
    parser.add_argument('--room', action='append', help='Target one room; repeatable')
    parser.add_argument('--rooms', action='append', help='Comma-separated list of rooms')
    parser.add_argument('--zone', action='append', help='Named zone from config; repeatable')
    parser.add_argument('--volume', type=int, help='Absolute announcement volume')
    parser.add_argument('--duck', type=int, default=10, help='Reduce current volume by this amount when audio is already active (default: 10)')
    parser.add_argument('--lang', default='en', help='gTTS language code')
    parser.add_argument('--slow', action='store_true', help='Use slower speech')
    parser.add_argument('--backend', choices=['gtts', 'elevenlabs'], help='TTS backend to use')
    parser.add_argument('--voice', help='Voice ID or preset for the selected backend')
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG, help='JSON config file with zone and TTS definitions')
    parser.add_argument('--no-restore', action='store_true', help='Do not restore previous playback state')
    parser.add_argument('--timeout', type=int, default=30, help='Seconds to wait before restore')
    args = parser.parse_args()

    config = load_config(args.config)
    targets = resolve_targets(args, config)

    cmd = [
        sys.executable,
        str(SONOS_TTS),
        '--targets-json',
        json.dumps(targets),
        '--duck',
        str(args.duck),
        '--lang',
        args.lang,
        '--timeout',
        str(args.timeout),
        '--config',
        str(args.config),
    ]
    if args.backend:
        cmd.extend(['--backend', args.backend])
    if args.voice:
        cmd.extend(['--voice', args.voice])
    if args.volume is not None:
        cmd.extend(['--volume', str(args.volume)])
    if args.slow:
        cmd.append('--slow')
    if args.no_restore:
        cmd.append('--no-restore')
    cmd.append(args.text)

    subprocess.run(cmd, check=True)


if __name__ == '__main__':
    main()

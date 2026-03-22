#!/usr/bin/env python3
import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

try:
    from gtts import gTTS
except Exception as e:
    print(f"Failed to import gTTS: {e}", file=sys.stderr)
    sys.exit(1)

DEFAULT_CACHE_DIR = Path('/home/jon/.openclaw/workspace/tts-cache')
DEFAULT_PORT = 8765


def run_sonos(args: list[str], room: str | None = None, capture: bool = False) -> str | None:
    cmd = ['sonos', *args]
    if room:
        cmd.extend(['--name', room])
    result = subprocess.run(cmd, check=True, text=True, capture_output=capture)
    return result.stdout if capture else None


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    finally:
        s.close()


def slugify(text: str, max_len: int = 48) -> str:
    cleaned = ''.join(ch.lower() if ch.isalnum() else '-' for ch in text)
    while '--' in cleaned:
        cleaned = cleaned.replace('--', '-')
    cleaned = cleaned.strip('-')
    return (cleaned[:max_len] or 'speech').strip('-') or 'speech'


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def ensure_http_server(cache_dir: Path, port: int):
    pid_file = cache_dir / 'http-server.pid'
    cache_dir.mkdir(parents=True, exist_ok=True)
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            if process_alive(pid):
                return
        except Exception:
            pass
        pid_file.unlink(missing_ok=True)

    log_file = cache_dir / 'http-server.log'
    cmd = [
        sys.executable,
        '-m', 'http.server',
        str(port),
        '--bind', '0.0.0.0',
        '--directory', str(cache_dir),
    ]
    with open(log_file, 'ab') as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=log, start_new_session=True)
    pid_file.write_text(str(proc.pid))
    time.sleep(0.5)
    if not process_alive(proc.pid):
        raise RuntimeError(f'HTTP server failed to start; see {log_file}')


def generate_mp3(text: str, cache_dir: Path, lang: str = 'en', slow: bool = False) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime('%Y%m%d-%H%M%S')
    name = f"{stamp}-{slugify(text)}.mp3"
    path = cache_dir / name
    tts = gTTS(text=text, lang=lang, slow=slow)
    tts.save(str(path))
    return path


def get_status(room: str) -> dict:
    raw = run_sonos(['status', '--format', 'json'], room=room, capture=True)
    return json.loads(raw or '{}')


def get_group_status() -> dict:
    raw = run_sonos(['group', 'status', '--format', 'json'], capture=True)
    return json.loads(raw or '{}')


def snapshot_group_map() -> dict[str, dict]:
    groups = get_group_status().get('groups', [])
    mapping: dict[str, dict] = {}
    for group in groups:
        coordinator = group.get('coordinator', {}).get('name')
        members = [member.get('name') for member in group.get('members', []) if member.get('name')]
        for member in members:
            mapping[member] = {'coordinator': coordinator, 'members': members}
    return mapping


def snapshot_state(room: str) -> dict:
    status = get_status(room)
    return {
        'transport_state': status.get('transport', {}).get('State'),
        'track_uri': status.get('position', {}).get('TrackURI'),
        'volume': status.get('volume'),
    }


def snapshot_targets(targets: list[str]) -> dict:
    group_map = snapshot_group_map()
    states = {}
    for room in targets:
        room_state = snapshot_state(room)
        room_state['group'] = group_map.get(room, {})
        states[room] = room_state
    return states


def announcement_volume(room: str, state: dict, explicit_volume: int | None, duck: int | None) -> int | None:
    if explicit_volume is not None:
        return explicit_volume
    current = state.get('volume')
    transport = state.get('transport_state')
    current_uri = state.get('track_uri')
    if duck is not None and current is not None and transport == 'PLAYING' and current_uri:
        return max(5, current - duck)
    return None


def sonos_play(room: str, url: str, volume: int | None = None):
    if volume is not None:
        run_sonos(['volume', 'set', str(volume)], room=room)
    run_sonos(['play-uri', url], room=room)


def wait_for_announcement(room: str, url: str, timeout: int = 30):
    deadline = time.time() + timeout
    saw_announcement = False
    while time.time() < deadline:
        try:
            status = get_status(room)
        except Exception:
            time.sleep(0.5)
            continue

        track_uri = status.get('position', {}).get('TrackURI')
        transport_state = status.get('transport', {}).get('State')

        if track_uri == url:
            saw_announcement = True
        elif saw_announcement:
            return

        if saw_announcement and transport_state in {'STOPPED', 'PAUSED_PLAYBACK'}:
            return

        time.sleep(0.5)


def restore_groups(previous: dict[str, dict]):
    seen_groups: set[tuple[str, tuple[str, ...]]] = set()
    for room, state in previous.items():
        group = state.get('group') or {}
        coordinator = group.get('coordinator')
        members = tuple(group.get('members', []))
        if not coordinator or not members:
            continue
        key = (coordinator, members)
        if key in seen_groups:
            continue
        seen_groups.add(key)

        if len(members) == 1:
            run_sonos(['group', 'unjoin'], room=members[0])
            continue

        run_sonos(['group', 'unjoin'], room=coordinator)
        for member in members:
            if member == coordinator:
                continue
            run_sonos(['group', 'join', '--to', coordinator], room=member)


def restore_states(previous: dict[str, dict], announcement_url: str):
    restore_groups(previous)
    for room, state in previous.items():
        previous_uri = state.get('track_uri')
        previous_volume = state.get('volume')
        previous_state = state.get('transport_state')

        if previous_volume is not None:
            run_sonos(['volume', 'set', str(previous_volume)], room=room)

        if previous_uri and previous_uri != announcement_url:
            run_sonos(['play-uri', previous_uri], room=room)
            if previous_state in {'PAUSED_PLAYBACK', 'STOPPED'}:
                run_sonos(['pause'], room=room)
        elif previous_state in {'PAUSED_PLAYBACK', 'STOPPED'}:
            run_sonos(['stop'], room=room)


def parse_targets(args) -> list[str]:
    if args.targets_json:
        targets = json.loads(args.targets_json)
        if not isinstance(targets, list) or not all(isinstance(x, str) for x in targets):
            raise SystemExit('--targets-json must be a JSON array of room names')
        return targets
    if args.sonos:
        return [args.sonos]
    return []


def main():
    parser = argparse.ArgumentParser(description='Generate TTS audio and optionally play it on Sonos')
    parser.add_argument('text', help='Text to speak')
    parser.add_argument('--sonos', metavar='ROOM', help='Target one Sonos room')
    parser.add_argument('--targets-json', help='JSON array of target Sonos room names')
    parser.add_argument('--volume', type=int, help='Absolute announcement volume')
    parser.add_argument('--duck', type=int, default=None, help='Reduce current volume by this amount when already playing')
    parser.add_argument('--lang', default='en', help='gTTS language code (default: en)')
    parser.add_argument('--slow', action='store_true', help='Use slower speech')
    parser.add_argument('--cache-dir', default=str(DEFAULT_CACHE_DIR), help='Directory for generated MP3 files')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='HTTP port for serving generated audio')
    parser.add_argument('--print-url', action='store_true', help='Print only the generated URL')
    parser.add_argument('--no-restore', action='store_true', help='Do not restore previous Sonos playback state after announcement')
    parser.add_argument('--timeout', type=int, default=30, help='Seconds to wait for announcement playback before restoring (default: 30)')
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir)
    mp3_path = generate_mp3(args.text, cache_dir=cache_dir, lang=args.lang, slow=args.slow)
    ensure_http_server(cache_dir=cache_dir, port=args.port)
    url = f'http://{get_local_ip()}:{args.port}/{quote(mp3_path.name)}'
    targets = parse_targets(args)

    if targets:
        previous = snapshot_targets(targets) if not args.no_restore else None
        for room in targets:
            effective_volume = announcement_volume(room, previous.get(room, {}) if previous else {}, args.volume, args.duck)
            sonos_play(room, url, volume=effective_volume)
        if previous is not None:
            wait_for_announcement(targets[0], url, timeout=args.timeout)
            restore_states(previous, url)
            print(f'Restored Sonos targets after announcement: {", ".join(targets)} :: {url}')
        else:
            print(f'Playing on Sonos targets [{", ".join(targets)}]: {url}')
    elif args.print_url:
        print(url)
    else:
        print(f'Generated: {mp3_path}\nURL: {url}')


if __name__ == '__main__':
    main()

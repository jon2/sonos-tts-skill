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

import requests

try:
    from gtts import gTTS
except Exception:
    gTTS = None

DEFAULT_CACHE_DIR = Path('/home/jon/.openclaw/workspace/tts-cache')
DEFAULT_PORT = 8765
DEFAULT_CONFIG = Path.home() / '.config' / 'sonos-tts' / 'config.json'


def load_config(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def get_tts_config(path: Path) -> dict:
    return load_config(path).get('tts', {})


def resolve_backend(cli_backend: str | None, tts_config: dict) -> str:
    return cli_backend or tts_config.get('backend') or 'gtts'


def resolve_elevenlabs_key(tts_config: dict) -> str | None:
    return os.environ.get('ELEVENLABS_API_KEY') or tts_config.get('elevenlabs', {}).get('apiKey')


def resolve_elevenlabs_voice(tts_config: dict, cli_voice: str | None) -> str | None:
    if cli_voice:
        return cli_voice
    return tts_config.get('elevenlabs', {}).get('voiceId')


def run_sonos(args: list[str], room: str | None = None, capture: bool = False, check: bool = True) -> str | None:
    cmd = ['sonos', *args]
    if room:
        cmd.extend(['--name', room])
    result = subprocess.run(cmd, check=check, text=True, capture_output=capture)
    return result.stdout if capture else None


def try_run_sonos(args: list[str], room: str | None = None):
    cmd = ['sonos', *args]
    if room:
        cmd.extend(['--name', room])
    result = subprocess.run(cmd, check=False, text=True, capture_output=True)
    return result.returncode, (result.stdout or '').strip(), (result.stderr or '').strip()


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
    cmd = [sys.executable, '-m', 'http.server', str(port), '--bind', '0.0.0.0', '--directory', str(cache_dir)]
    with open(log_file, 'ab') as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=log, start_new_session=True)
    pid_file.write_text(str(proc.pid))
    time.sleep(0.5)
    if not process_alive(proc.pid):
        raise RuntimeError(f'HTTP server failed to start; see {log_file}')


def generate_mp3_gtts(text: str, path: Path, lang: str = 'en', slow: bool = False):
    if gTTS is None:
        raise RuntimeError('gTTS is not installed/importable')
    tts = gTTS(text=text, lang=lang, slow=slow)
    tts.save(str(path))


def generate_mp3_elevenlabs(text: str, path: Path, voice_id: str, api_key: str, model_id: str | None = None):
    url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
    payload = {
        'text': text,
        'model_id': model_id or 'eleven_multilingual_v2',
        'output_format': 'mp3_44100_128',
    }
    headers = {
        'xi-api-key': api_key,
        'Content-Type': 'application/json',
        'Accept': 'audio/mpeg',
    }
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    if response.status_code >= 400:
        raise RuntimeError(f'ElevenLabs TTS failed: {response.status_code} {response.text[:500]}')
    path.write_bytes(response.content)


def generate_mp3(text: str, cache_dir: Path, backend: str, lang: str = 'en', slow: bool = False, voice: str | None = None, config_path: Path | None = None) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime('%Y%m%d-%H%M%S')
    name = f"{stamp}-{slugify(text)}.mp3"
    path = cache_dir / name
    tts_config = get_tts_config(config_path or DEFAULT_CONFIG)

    if backend == 'gtts':
        generate_mp3_gtts(text, path, lang=lang, slow=slow)
    elif backend == 'elevenlabs':
        api_key = resolve_elevenlabs_key(tts_config)
        voice_id = resolve_elevenlabs_voice(tts_config, voice)
        model_id = tts_config.get('elevenlabs', {}).get('modelId')
        if not api_key:
            raise RuntimeError('ElevenLabs backend selected but no API key found. Set ELEVENLABS_API_KEY or add tts.elevenlabs.apiKey to config.')
        if not voice_id:
            raise RuntimeError('ElevenLabs backend selected but no voice ID found. Use --voice or add tts.elevenlabs.voiceId to config.')
        generate_mp3_elevenlabs(text, path, voice_id=voice_id, api_key=api_key, model_id=model_id)
    else:
        raise RuntimeError(f'Unsupported TTS backend: {backend}')

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


def announcement_volume(state: dict, explicit_volume: int | None, duck: int | None) -> int | None:
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
    for _, state in previous.items():
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
    restored_group_playback: set[str] = set()
    for room, state in previous.items():
        previous_volume = state.get('volume')
        if previous_volume is not None:
            run_sonos(['volume', 'set', str(previous_volume)], room=room)
    for room, state in previous.items():
        group = state.get('group') or {}
        coordinator = group.get('coordinator') or room
        members = group.get('members') or [room]
        is_group = len(members) > 1
        if is_group and room != coordinator:
            continue
        if coordinator in restored_group_playback:
            continue
        coordinator_state = previous.get(coordinator, state)
        previous_uri = coordinator_state.get('track_uri')
        previous_state = coordinator_state.get('transport_state')
        should_restore_uri = previous_uri and previous_uri != announcement_url and previous_state == 'PLAYING'
        if should_restore_uri:
            run_sonos(['play-uri', previous_uri], room=coordinator)
        elif previous_state in {'PAUSED_PLAYBACK', 'STOPPED'}:
            try_run_sonos(['stop'], room=coordinator)
        restored_group_playback.add(coordinator)


def prepare_synchronized_group(targets: list[str], previous: dict[str, dict], explicit_volume: int | None, duck: int | None) -> str:
    coordinator = targets[0]
    run_sonos(['group', 'unjoin'], room=coordinator)
    for member in targets[1:]:
        run_sonos(['group', 'unjoin'], room=member)
    for member in targets[1:]:
        run_sonos(['group', 'join', '--to', coordinator], room=member)
    for room in targets:
        effective_volume = announcement_volume(previous.get(room, {}), explicit_volume, duck)
        if effective_volume is not None:
            run_sonos(['volume', 'set', str(effective_volume)], room=room)
    return coordinator


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
    parser.add_argument('--backend', choices=['gtts', 'elevenlabs'], help='TTS backend to use')
    parser.add_argument('--voice', help='Voice ID or preset for the selected backend')
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG, help='JSON config file for zones and TTS backend settings')
    parser.add_argument('--cache-dir', default=str(DEFAULT_CACHE_DIR), help='Directory for generated MP3 files')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='HTTP port for serving generated audio')
    parser.add_argument('--print-url', action='store_true', help='Print only the generated URL')
    parser.add_argument('--no-restore', action='store_true', help='Do not restore previous Sonos playback state after announcement')
    parser.add_argument('--timeout', type=int, default=30, help='Seconds to wait for announcement playback before restoring (default: 30)')
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir)
    backend = resolve_backend(args.backend, get_tts_config(args.config))
    mp3_path = generate_mp3(args.text, cache_dir=cache_dir, backend=backend, lang=args.lang, slow=args.slow, voice=args.voice, config_path=args.config)
    ensure_http_server(cache_dir=cache_dir, port=args.port)
    url = f'http://{get_local_ip()}:{args.port}/{quote(mp3_path.name)}'
    targets = parse_targets(args)

    if targets:
        previous = snapshot_targets(targets) if not args.no_restore else None
        if len(targets) == 1:
            room = targets[0]
            effective_volume = announcement_volume(previous.get(room, {}) if previous else {}, args.volume, args.duck)
            sonos_play(room, url, volume=effective_volume)
            wait_room = room
        else:
            coordinator = prepare_synchronized_group(targets, previous or {}, args.volume, args.duck)
            sonos_play(coordinator, url, volume=None)
            wait_room = coordinator
        if previous is not None:
            wait_for_announcement(wait_room, url, timeout=args.timeout)
            restore_states(previous, url)
            print(f'Restored Sonos targets after synchronized announcement: {", ".join(targets)} :: {url}')
        else:
            print(f'Playing on Sonos targets [{", ".join(targets)}]: {url}')
    elif args.print_url:
        print(url)
    else:
        print(f'Generated: {mp3_path}\nURL: {url}')


if __name__ == '__main__':
    main()

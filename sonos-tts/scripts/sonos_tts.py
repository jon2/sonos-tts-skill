#!/usr/bin/env python3
import argparse
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


def sonos_play(room: str, url: str, volume: int | None = None):
    if volume is not None:
        subprocess.run(['sonos', 'volume', 'set', str(volume), '--name', room], check=True)
    subprocess.run(['sonos', 'play-uri', '--name', room, url], check=True)


def main():
    parser = argparse.ArgumentParser(description='Generate TTS audio and optionally play it on Sonos')
    parser.add_argument('text', help='Text to speak')
    parser.add_argument('--sonos', metavar='ROOM', help='Sonos room name to play on')
    parser.add_argument('--volume', type=int, help='Set Sonos volume before playback')
    parser.add_argument('--lang', default='en', help='gTTS language code (default: en)')
    parser.add_argument('--slow', action='store_true', help='Use slower speech')
    parser.add_argument('--cache-dir', default=str(DEFAULT_CACHE_DIR), help='Directory for generated MP3 files')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='HTTP port for serving generated audio')
    parser.add_argument('--print-url', action='store_true', help='Print only the generated URL')
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir)
    mp3_path = generate_mp3(args.text, cache_dir=cache_dir, lang=args.lang, slow=args.slow)
    ensure_http_server(cache_dir=cache_dir, port=args.port)
    url = f'http://{get_local_ip()}:{args.port}/{quote(mp3_path.name)}'

    if args.sonos:
        sonos_play(args.sonos, url, volume=args.volume)
        print(f'Playing on Sonos [{args.sonos}]: {url}')
    elif args.print_url:
        print(url)
    else:
        print(f'Generated: {mp3_path}\nURL: {url}')


if __name__ == '__main__':
    main()

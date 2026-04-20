#!/usr/bin/env python3
import asyncio
import aiohttp
from aiohttp import web
import subprocess
import threading
import contextlib
import os
import json
import time

PORT = 3078
XDISPLAY = ":99"
GAME_W, GAME_H = 1024, 768
FPS = 30
FRAME_QUEUE_SIZE = 3

_frame_queue: asyncio.Queue = None
_active: bool = False
_held_keys: set = set()
_game_proc: subprocess.Popen = None

KEYMAP = {
    'ArrowLeft':  'Left',
    'ArrowRight': 'Right',
    'ArrowUp':    'Up',
    'ArrowDown':  'Down',
    'Enter':      'Return',
    ' ':          'space',
    'Escape':     'Escape',
    'Backspace':  'BackSpace',
    'Delete':     'Delete',
    'F1': 'F1', 'F2': 'F2', 'F3': 'F3',
}

_XENV = None  # set in main()


def _xdotool(*args):
    subprocess.run(
        ['xdotool', *args],
        env=_XENV,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def inject_key(key: str, is_down: bool):
    xkey = KEYMAP.get(key)
    if xkey is None and len(key) == 1 and (key.isalpha() or key.isdigit()):
        xkey = key.lower()
    if not xkey:
        return
    if is_down:
        _held_keys.add(xkey)
    else:
        _held_keys.discard(xkey)
    _xdotool('keydown' if is_down else 'keyup', '--clearmodifiers', xkey)


def release_all_keys():
    for k in list(_held_keys):
        _xdotool('keyup', '--clearmodifiers', k)
    _held_keys.clear()


def _focus_game_window():
    try:
        subprocess.run(
            ['xdotool', 'search', '--sync', '--name', 'DATA BREACH', 'windowfocus', '%@'],
            env={**os.environ, 'DISPLAY': XDISPLAY},
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=8,
        )
    except Exception as e:
        print(f'[DATA BREACH] Window focus skipped ({e})', flush=True)


def _spawn_game():
    """Start the game subprocess. Used both at startup and by the watchdog."""
    global _game_proc
    env = {
        **os.environ,
        'DISPLAY': XDISPLAY,
        'SDL_VIDEODRIVER': 'x11',
        'SDL_AUDIODRIVER': 'dummy',
    }
    _game_proc = subprocess.Popen(
        ['python3', '/app/databreach.py'],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _mjpeg_reader(proc: subprocess.Popen, loop: asyncio.AbstractEventLoop, q: asyncio.Queue):
    """Parse MJPEG stream from ffmpeg stdout and push frames into asyncio queue.

    Thread-safe: all queue interactions happen via run_coroutine_threadsafe,
    and the coroutine runs in the event loop where asyncio.Queue is safe.
    """
    async def _put(f):
        if q.full():
            with contextlib.suppress(asyncio.QueueEmpty):
                q.get_nowait()
        await q.put(f)

    buf = b''
    while True:
        chunk = proc.stdout.read(32768)
        if not chunk:
            break
        buf += chunk
        while True:
            s = buf.find(b'\xff\xd8')
            if s == -1:
                buf = b''
                break
            e = buf.find(b'\xff\xd9', s + 2)
            if e == -1:
                buf = buf[s:]
                break
            frame = buf[s:e + 2]
            buf = buf[e + 2:]
            asyncio.run_coroutine_threadsafe(_put(frame), loop)


async def ws_handler(request):
    global _active

    # Atomic claim BEFORE any await — prevents two connections bypassing the busy check
    if _active:
        ws = web.WebSocketResponse(heartbeat=15)
        await ws.prepare(request)
        await ws.send_json({'type': 'busy'})
        await ws.close()
        return ws
    _active = True

    ws = web.WebSocketResponse(heartbeat=15)
    await ws.prepare(request)

    async def stream():
        while not ws.closed:
            try:
                frame = await asyncio.wait_for(_frame_queue.get(), timeout=3.0)
                await ws.send_bytes(frame)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

    streamer = asyncio.create_task(stream())
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    d = json.loads(msg.data)
                    if d.get('type') in ('keydown', 'keyup'):
                        inject_key(d['key'], d['type'] == 'keydown')
                except Exception:
                    pass
            elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                break
    finally:
        streamer.cancel()
        release_all_keys()
        _active = False

    return ws


async def index_handler(request):
    return web.FileResponse('/app/static/index.html')


async def health_handler(request):
    ok = _game_proc is not None and _game_proc.poll() is None
    return web.json_response({'ok': ok}, status=200 if ok else 503)


def _start_services(loop: asyncio.AbstractEventLoop, q: asyncio.Queue):
    # Remove stale X lock from a previous crash/restart
    lock = f'/tmp/.X{XDISPLAY.lstrip(":")}-lock'
    with contextlib.suppress(FileNotFoundError):
        os.remove(lock)

    # Xvfb virtual display
    subprocess.Popen(
        ['Xvfb', XDISPLAY, '-screen', '0', f'{GAME_W}x{GAME_H}x24'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1.5)
    print('[DATA BREACH] Xvfb started', flush=True)

    # Game process
    _spawn_game()
    time.sleep(3.0)

    _focus_game_window()
    print('[DATA BREACH] Game started', flush=True)

    # ffmpeg: capture Xvfb and output MJPEG frames to stdout
    ffmpeg = subprocess.Popen(
        [
            'ffmpeg', '-loglevel', 'quiet',
            '-f', 'x11grab', '-r', str(FPS),
            '-video_size', f'{GAME_W}x{GAME_H}',
            '-i', f'{XDISPLAY}.0+0,0',
            '-f', 'mjpeg', '-q:v', '4',
            'pipe:1',
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    threading.Thread(
        target=_mjpeg_reader, args=(ffmpeg, loop, q), daemon=True
    ).start()
    print(f'[DATA BREACH] Streaming started at {FPS}fps', flush=True)


async def watchdog():
    """Restart the game if it exits (e.g. user hit QUIT or Q on the menu)."""
    while True:
        await asyncio.sleep(5)
        if _game_proc is not None and _game_proc.poll() is not None:
            print('[DATA BREACH] Game exited, restarting...', flush=True)
            _spawn_game()
            await asyncio.sleep(2.5)
            _focus_game_window()


async def main():
    global _frame_queue, _XENV

    _XENV = {**os.environ, 'DISPLAY': XDISPLAY}
    _frame_queue = asyncio.Queue(maxsize=FRAME_QUEUE_SIZE)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: _start_services(loop, _frame_queue))

    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', ws_handler)
    app.router.add_get('/health', health_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()
    print(f'[DATA BREACH] Server live → http://0.0.0.0:{PORT}', flush=True)

    asyncio.create_task(watchdog())
    await asyncio.Event().wait()


if __name__ == '__main__':
    asyncio.run(main())

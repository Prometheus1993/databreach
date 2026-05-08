#!/usr/bin/env python3
import asyncio
import aiohttp
from aiohttp import web
import subprocess
import contextlib
import os
import time

PORT = 3078
XDISPLAY = ":99"
GAME_W, GAME_H = 1024, 768
VNC_PORT = 5900
MAX_SESSION_SECONDS = 600  # 10 min hard cap
NOVNC_PATH = '/usr/share/novnc'

_current_ws: web.WebSocketResponse = None
_game_proc: subprocess.Popen = None


def _spawn_game():
    global _game_proc
    env = {
        **os.environ,
        'DISPLAY': XDISPLAY,
        'SDL_VIDEODRIVER': 'x11',
        'SDL_AUDIODRIVER': 'dummy',
        'SDL_VIDEO_CENTERED': '1',
        'SDL_VIDEO_WINDOW_POS': '0,0',
    }
    _game_proc = subprocess.Popen(
        ['python3', '-u', '/app/databreach.py'],
        env=env,
    )


async def status_handler(request):
    busy = _current_ws is not None and not _current_ws.closed
    return web.json_response({'busy': busy})


async def ws_handler(request):
    global _current_ws

    # If there's an existing session, boot it so the new client takes over.
    if _current_ws is not None and not _current_ws.closed:
        with contextlib.suppress(Exception):
            await _current_ws.close(code=4000, message=b'superseded')

    ws = web.WebSocketResponse(protocols=('binary',), max_msg_size=0)
    await ws.prepare(request)
    _current_ws = ws

    try:
        reader, writer = await asyncio.open_connection('127.0.0.1', VNC_PORT)
    except Exception as e:
        print(f'[DATA BREACH] VNC connect failed: {e}', flush=True)
        await ws.close(code=4002)
        return ws

    session_start = time.monotonic()

    async def ws_to_vnc():
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.BINARY:
                writer.write(msg.data)
                try:
                    await writer.drain()
                except Exception:
                    break
            elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                break

    async def vnc_to_ws():
        try:
            while not ws.closed:
                data = await reader.read(32768)
                if not data:
                    break
                await ws.send_bytes(data)
        except Exception:
            pass

    async def timeout_guard():
        while not ws.closed:
            await asyncio.sleep(5)
            if time.monotonic() - session_start >= MAX_SESSION_SECONDS:
                await ws.close(code=4003, message=b'session_limit')
                return

    tasks = [
        asyncio.create_task(ws_to_vnc()),
        asyncio.create_task(vnc_to_ws()),
        asyncio.create_task(timeout_guard()),
    ]
    try:
        _done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
    finally:
        with contextlib.suppress(Exception):
            writer.close()
            await writer.wait_closed()
        if not ws.closed:
            await ws.close()
        if _current_ws is ws:
            _current_ws = None

    return ws


async def index_handler(request):
    return web.FileResponse('/app/static/index.html')


async def health_handler(request):
    ok = _game_proc is not None and _game_proc.poll() is None
    return web.json_response({'ok': ok}, status=200 if ok else 503)


def _start_services():
    lock = f'/tmp/.X{XDISPLAY.lstrip(":")}-lock'
    with contextlib.suppress(FileNotFoundError):
        os.remove(lock)

    subprocess.Popen(
        ['Xvfb', XDISPLAY, '-screen', '0', f'{GAME_W}x{GAME_H}x24', '-ac'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1.5)
    print('[DATA BREACH] Xvfb started', flush=True)

    subprocess.Popen(
        ['matchbox-window-manager', '-use_cursor', 'no', '-use_titlebar', 'no'],
        env={**os.environ, 'DISPLAY': XDISPLAY},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(0.5)
    print('[DATA BREACH] Matchbox WM started', flush=True)

    _spawn_game()
    time.sleep(3.0)
    print('[DATA BREACH] Game started', flush=True)

    subprocess.Popen(
        [
            'x11vnc',
            '-display', XDISPLAY,
            '-forever',
            '-shared',
            '-nopw',
            '-quiet',
            '-localhost',
            '-rfbport', str(VNC_PORT),
            '-nocursor',
            '-threads',
            '-ncache', '0',
            # Scan/defer kept loose (~30 Hz) so we don't burn CPU encoding
            # every tiny pixel diff from the matrix rain / CRT scanlines —
            # the game still feels responsive but bandwidth stays tame.
            '-wait', '30',
            '-defer', '30',
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1.5)
    print(f'[DATA BREACH] x11vnc listening on {VNC_PORT}', flush=True)


async def watchdog():
    while True:
        await asyncio.sleep(5)
        if _game_proc is not None and _game_proc.poll() is not None:
            print('[DATA BREACH] Game exited, restarting...', flush=True)
            _spawn_game()


async def main():
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _start_services)

    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', ws_handler)
    app.router.add_get('/status', status_handler)
    app.router.add_get('/health', health_handler)
    app.router.add_static('/novnc/', NOVNC_PATH)

    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()
    print(f'[DATA BREACH] Server live → http://0.0.0.0:{PORT}', flush=True)

    asyncio.create_task(watchdog())
    await asyncio.Event().wait()


if __name__ == '__main__':
    asyncio.run(main())

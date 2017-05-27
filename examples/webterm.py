"""
    webterm
    ~~~~~~~

    An example showing how to use :mod:`pyte` to implement a basic
    single-user web terminal.

    .. note:: This example requires at least Python 3.5 and a recent
              version of ``aiohttp`` library.

    :copyright: (c) 2017 by pyte authors and contributors,
                see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

import json
import os
import pty
import shlex
import signal
import webbrowser
from pathlib import Path

import aiohttp
import asyncio
from aiohttp import web

import pyte


class Terminal:
    def __init__(self, columns, lines, p_in):
        self.screen = pyte.DiffScreen(columns, lines)
        self.screen.set_mode(pyte.modes.LNM)
        self.screen.write_process_input = \
            lambda data: p_in.write(data.encode())
        self.stream = pyte.ByteStream()
        self.stream.attach(self.screen)

    def feed(self, data):
        self.stream.feed(data)

    def dumps(self):
        cursor = self.screen.cursor
        lines = []
        for y in self.screen.dirty:
            line = self.screen.buffer[y]
            data = [(char.data, char.reverse, char.fg, char.bg)
                    for char in (line[x] for x in range(self.screen.columns))]
            lines.append((y, data))

        self.screen.dirty.clear()
        return json.dumps({"c": (cursor.x, cursor.y), "lines": lines})


def open_terminal(command="bash", columns=80, lines=24):
    p_pid, master_fd = pty.fork()
    if p_pid == 0:  # Child.
        argv = shlex.split(command)
        env = dict(TERM="linux", LC_ALL="en_GB.UTF-8",
                   COLUMNS=str(columns), LINES=str(lines))
        os.execvpe(argv[0], argv, env)

    # File-like object for I/O with the child process aka command.
    p_out = os.fdopen(master_fd, "w+b", 0)
    return Terminal(columns, lines, p_out), p_pid, p_out


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    request.app["websockets"].add(asyncio.Task.current_task())

    terminal, p_pid, p_out = open_terminal()
    ws.send_str(terminal.dumps())

    def on_master_output():
        terminal.feed(p_out.read(65536))
        ws.send_str(terminal.dumps())

    loop = asyncio.get_event_loop()
    loop.add_reader(p_out, on_master_output)
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                p_out.write(msg.data.encode())
            elif msg.type == aiohttp.WSMsgType.ERROR:
                raise ws.exception()
    except (asyncio.CancelledError,
            OSError):  # Process died?
        pass
    finally:
        loop.remove_reader(p_out)
        os.kill(p_pid, signal.SIGTERM)
        p_out.close()
        if not is_shutting_down:
            request.app["websockets"].remove(asyncio.Task.current_task())
    await ws.close()
    return ws


is_shutting_down = False


async def on_shutdown(app):
    """Closes all WS connections on shutdown."""
    global is_shutting_down
    is_shutting_down = True
    for task in app["websockets"]:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    app = web.Application()
    app["websockets"] = set()
    app.router.add_get("/ws", websocket_handler)
    app.router.add_static("/", Path(__file__).parent / "static",
                          show_index=True)
    app.on_shutdown.append(on_shutdown)

    webbrowser.open_new_tab("http://localhost:8080/index.html")

    web.run_app(app)

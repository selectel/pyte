"""
    webterm
    ~~~~~~~

    An example showing how to use :mod:`pyte` to implement a basic
    single-user web terminal.

    Client-side ``webterm.js`` supports
    * incremental rendering via :data:`~pyte.screens.DiffScreen.dirty`,
    * most of the common keyboard events,
    * pagination on Meta + P/Meta + A.

    .. note:: This example requires at least Python 3.7 and version 3.0 of the
              ``aiohttp`` library.

    .. seealso::

       `The TTY demystified <http://www.linusakesson.net/programming/tty>`_
       for an introduction to the inner workings of the TTY subsystem.

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
        self.screen = pyte.HistoryScreen(columns, lines)
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

    request.app["websockets"].add(asyncio.current_task())

    terminal, p_pid, p_out = open_terminal()
    await ws.send_str(terminal.dumps())

    def on_master_output():
        terminal.feed(p_out.read(65536))
        asyncio.create_task(ws.send_str(terminal.dumps()))

    loop = asyncio.get_event_loop()
    loop.add_reader(p_out, on_master_output)
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == pyte.control.ESC + "N":
                    terminal.screen.next_page()
                    ws.send_str(terminal.dumps())
                elif msg.data == pyte.control.ESC + "P":
                    terminal.screen.prev_page()
                    ws.send_str(terminal.dumps())
                else:
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
            request.app["websockets"].remove(asyncio.current_task())
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

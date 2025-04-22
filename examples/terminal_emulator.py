"""
    terminal_emulator
    ~~~~~~~~~~~~~~~~~

    An example showing how to use :mod:`pyte` to implement a basic
    terminal emulator using Textual.
    To exit the application, hit Ctrl-C.

    .. note:: This example requires the ``textual`` library, at least v0.6.0.

    :copyright: (c) 2022 by pyte authors and contributors,
                see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

import asyncio
import fcntl
import os
import pty
import shlex
import struct
import termios

import pyte
from rich.text import Text
from textual import events
from textual.app import App
from textual.widget import Widget


class PyteDisplay:
    def __init__(self, lines):
        self.lines = lines

    def __rich_console__(self, console, options):
        yield from self.lines


class Terminal(Widget, can_focus=True):
    def __init__(self, send_queue, recv_queue, ncol, nrow):
        self.ctrl_keys = {
            "left": "\u001b[D",
            "right": "\u001b[C",
            "up": "\u001b[A",
            "down": "\u001b[B",
        }
        self.recv_queue = recv_queue
        self.send_queue = send_queue
        self.nrow = nrow
        self.ncol = ncol
        self._display = PyteDisplay([Text()])
        self._screen = pyte.Screen(self.ncol, self.nrow)
        self.stream = pyte.Stream(self._screen)
        asyncio.create_task(self.recv())
        super().__init__()
        self.focus()

    def render(self):
        return self._display

    async def on_key(self, event: events.Key) -> None:
        char = self.ctrl_keys.get(event.key) or event.character
        await self.send_queue.put(["stdin", char])

    async def recv(self):
        while True:
            message = await self.recv_queue.get()
            cmd = message[0]
            if cmd == "setup":
                await self.send_queue.put(["set_size", self.nrow, self.ncol, 567, 573])
            elif cmd == "stdout":
                chars = message[1]
                self.stream.feed(chars)
                lines = []
                for i, line in enumerate(self._screen.display):
                    text = Text.from_ansi(line)
                    x = self._screen.cursor.x
                    if i == self._screen.cursor.y and x < len(text):
                        cursor = text[x]
                        cursor.stylize("reverse")
                        new_text = text[:x]
                        new_text.append(cursor)
                        new_text.append(text[x + 1:])
                        text = new_text
                    lines.append(text)
                self._display = PyteDisplay(lines)
                self.refresh()


class TerminalEmulator(App):

    def __init__(self, ncol, nrow):
        self.ncol = ncol
        self.nrow = nrow
        self.data_or_disconnect = None
        self.fd = self.open_terminal()
        self.p_out = os.fdopen(self.fd, "w+b", 0)
        self.recv_queue = asyncio.Queue()
        self.send_queue = asyncio.Queue()
        self.event = asyncio.Event()
        super().__init__()

    def compose(self):
        asyncio.create_task(self._run())
        asyncio.create_task(self._send_data())
        yield Terminal(self.recv_queue, self.send_queue, self.ncol, self.nrow)

    def open_terminal(self):
        pid, fd = pty.fork()
        if pid == 0:
            argv = shlex.split("bash")
            env = dict(TERM="linux", LC_ALL="en_GB.UTF-8", COLUMNS=str(self.ncol), LINES=str(self.nrow))
            os.execvpe(argv[0], argv, env)
        return fd

    async def _run(self):
        loop = asyncio.get_running_loop()

        def on_output():
            try:
                self.data_or_disconnect = self.p_out.read(65536).decode()
                self.event.set()
            except Exception:
                loop.remove_reader(self.p_out)
                self.data_or_disconnect = None
                self.event.set()

        loop.add_reader(self.p_out, on_output)
        await self.send_queue.put(["setup", {}])
        while True:
            msg = await self.recv_queue.get()
            if msg[0] == "stdin":
                self.p_out.write(msg[1].encode())
            elif msg[0] == "set_size":
                winsize = struct.pack("HH", msg[1], msg[2])
                fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)

    async def _send_data(self):
        while True:
            await self.event.wait()
            self.event.clear()
            if self.data_or_disconnect is None:
                await self.send_queue.put(["disconnect", 1])
            else:
                await self.send_queue.put(["stdout", self.data_or_disconnect])


if __name__ == "__main__":
    app = TerminalEmulator(80, 24)
    app.run()

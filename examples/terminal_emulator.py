"""
    terminal_emulator
    ~~~~~~~~~~~~~~~~~

    An example showing how to use :mod:`pyte` to implement a basic
    terminal emulator using Textual.
    To exit the application, hit Ctrl-C.

    .. note:: This example requires the ``textual`` library, at least v0.5.0.

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
from io import StringIO

import pyte
from rich.console import Console, RenderableType
from rich.text import Text
from textual import events
from textual.app import App
from textual.widget import Widget


CONSOLE = Console(file=StringIO(), force_terminal=True, force_interactive=False)

CTRL_KEYS = {
    "left": "\u001b[D",
    "right": "\u001b[C",
    "up": "\u001b[A",
    "down": "\u001b[B",
}


def open_terminal(command="bash", columns=80, lines=24):
    pid, fd = pty.fork()
    if pid == 0:
        argv = shlex.split(command)
        env = dict(TERM="linux", LC_ALL="en_GB.UTF-8", COLUMNS=str(columns), LINES=str(lines))
        os.execvpe(argv[0], argv, env)
    return fd


class Terminal(Widget, can_focus=True):
    def __init__(self, send_queue, recv_queue):
        self.recv_queue = recv_queue
        self.send_queue = send_queue
        self.chars = ""
        self._screen = pyte.Screen(80, 24)
        self.stream = pyte.Stream(self._screen)
        asyncio.create_task(self.recv())
        super().__init__()
        self.focus()

    def render(self) -> RenderableType:
        return self.chars

    async def on_key(self, event: events.Key) -> None:
        char = CTRL_KEYS.get(event.key) or event.char
        await self.send_queue.put(["stdin", char])

    async def recv(self):
        while True:
            message = await self.recv_queue.get()
            cmd = message[0]
            if cmd == "setup":
                await self.send_queue.put(["set_size", 24, 80, 567, 573])
            elif cmd == "stdout":
                chars = message[1]
                self.stream.feed(chars)
                with CONSOLE.capture() as capture:
                    for i, line in enumerate(self._screen.display):
                        text = Text.from_ansi(line)
                        x = self._screen.cursor.x
                        if x < len(text) and  i == self._screen.cursor.y:
                            CONSOLE.print(text[:x], end="")
                            CONSOLE.print(text[x], style="reverse", end="")
                            CONSOLE.print(text[x + 1:])
                        else:
                            CONSOLE.print(text)
                self.chars = capture.get()
                self.refresh()


class TerminalEmulator(App):

    def __init__(self):
        self.data_or_disconnect = None
        self.fd = open_terminal()
        self.p_out = os.fdopen(self.fd, "w+b", 0)
        self.recv_queue = asyncio.Queue()
        self.send_queue = asyncio.Queue()
        self.event = asyncio.Event()
        super().__init__()

    def compose(self):
        asyncio.create_task(self._run())
        asyncio.create_task(self._send_data())
        yield Terminal(self.recv_queue, self.send_queue)

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
    app = TerminalEmulator()
    app.run()

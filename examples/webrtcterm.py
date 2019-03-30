import pty
import shlex
import signal
import argparse
import asyncio
import json
import logging
import os
import ssl
import uuid

from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
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

pc = None
datachannel = None
p_pid = None
p_out = None
ROOT = os.path.dirname(__file__)
logger = logging.getLogger('webrtcterm')

async def index(request):
    content = open(os.path.join(ROOT, 'static', 'webrtcterm.html'), 'r').read()
    return web.Response(content_type='text/html', text=content)

async def javascript(request):
    content = open(os.path.join(ROOT, 'static', 'webrtcterm.js'), 'r').read()
    return web.Response(content_type='application/javascript', text=content)

async def css(request):
    content = open(os.path.join(ROOT, 'static', 'base16-eighties-dark.css'), 'r').read()
    return web.Response(content_type='text/css', text=content)

async def on_shutdown(app):
    # close peer connections
    pc.close()

def channel_log(channel, t, message):
    print('channel(%s) %s %s' % (channel.label, t, message))

def channel_send(channel, message):
    if channel is None:
        logger.error('channel is None, dropping a message:\t{}'.format(message))
        return
    channel_log(channel, '>', message)
    channel.send(message)

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(
        sdp=params['sdp'],
        type=params['type'])

    pc = RTCPeerConnection()
    pc_id = 'PeerConnection(%s)' % uuid.uuid4()

    @pc.on('datachannel')
    def on_datachannel(channel):
        logger.info('got a data channel {}'.format(channel.label))
        datachannel = channel
        logger.info('set datachannel as {}'.format(datachannel.label))

        # finally, open a terminal
        terminal, p_pid, p_out = open_terminal()
        def on_master_output():
            terminal.feed(p_out.read(65536))
            channel_send(datachannel, terminal.dumps())
        loop = asyncio.get_event_loop()
        loop.add_reader(p_out, on_master_output)

        @channel.on('message')
        def on_message(message):
            logger.info('a message arrived:\t{}'.format(message))
            # a command arrived
            if message == pyte.control.ESC + "N":
                terminal.screen.next_page()
                channel_send(datachannel, terminal.dumps())
            elif message == pyte.control.ESC + "P":
                terminal.screen.prev_page()
                channel_send(datachannel, terminal.dumps())
            else:
                p_out.write(message.encode())

    @pc.on('iceconnectionstatechange')
    async def on_iceconnectionstatechange():
        logger.info('ICE connection state is %s', pc.iceConnectionState)
        if pc.iceConnectionState == 'failed':
            await pc.close()

    # handle offer
    await pc.setRemoteDescription(offer)

    # create answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type='application/json',
        text=json.dumps({
            'sdp': pc.localDescription.sdp,
            'type': pc.localDescription.type
        }))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='WebRTC datachannel terminal demo')
    parser.add_argument('--cert-file', help='SSL certificate file (for HTTPS)')
    parser.add_argument('--key-file', help='SSL key file (for HTTPS)')
    parser.add_argument('--port', type=int, default=8080,
                        help='Port for HTTP server (default: 8080)')
    parser.add_argument('--verbose', '-v', action='count')
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.cert_file:
        ssl_context = ssl.SSLContext()
        ssl_context.load_cert_chain(args.cert_file, args.key_file)
    else:
        ssl_context = None

    app = web.Application()
    app.router.add_get('/index.html', index)
    app.router.add_get('/base16-eighties-dark.css', css)
    app.router.add_get('/webrtcterm.js', javascript)
    app.router.add_post('/offer', offer)
    try:
        web.run_app(app, access_log=None, port=args.port, ssl_context=ssl_context)
    finally:
        if pc is not None:
            pc.close()
        if p_pid is not None:
            logger.info('terminating a terminal process')
            os.kill(p_pid, signal.SIGTERM)
            p_out.close()
    logger.info('finished running')

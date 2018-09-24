#!/usr/bin/env python3.7

"""
Usage: teamserver.py <host> <password> [-h] [-v] [--port <PORT>] 
                [--insecure]

optional arguments:
    -h, --help          Show this help message and exit
    -v, --version       Show version
    -p, --port <PORT>   Port to bind to [default: 5000]
    --insecure          Start server without TLS
"""

import asyncio
import json
import logging
import ssl
import pathlib
import websockets
import signal
import http
import functools
import hmac
import traceback
from core.events import NEW_SESSION, NEW_USER, SESSION_STAGED, NEW_LISTENER, SERVER_STATS
from core.eventlistener import ThreadedEventListener
from core.utils import decode_auth_header
from core import Users, Listeners, Modules, Sessions
from websockets import WebSocketServerProtocol
from docopt import docopt
from hashlib import sha512
from typing import Dict, List, Any

logging.basicConfig(format="%(asctime)s %(process)d %(threadName)s - [%(levelname)s] %(filename)s: %(funcName)s - %(message)s", level=logging.DEBUG)

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(
    pathlib.Path(__file__).with_name('test.pem')
)


class TeamServer:
    def __init__(self):
        self.event_listener = ThreadedEventListener(loop=asyncio.get_running_loop())

        self.users = Users()
        self.listeners = Listeners()
        self.sessions = Sessions(self.listeners)

        #self.modules = Modules()
        #self.events = Events()

        self.event_listener.attach(SESSION_STAGED, self.users.broadcast_message)
        self.event_listener.attach(NEW_SESSION, self.users.broadcast_message)
        self.event_listener.attach(NEW_SESSION, self.update_stats)
        self.event_listener.attach(NEW_LISTENER, self.update_stats)

        self.event_listener.start()

    async def update_stats(self):
        stats = {
            'sessions': len(self.sessions),
            'listeners': len(self.listeners),
            'users': len(self.users)
        }

        await self.users.broadcast_event(SERVER_STATS, stats)

    async def process(self, websocket, message: Dict[str, Any]):
        # I hate everything in here, but that'll do pig... that'll do...
        success = True

        try:
            ctx = getattr(self, message['ctx'].lower())
            try:
                result = getattr(ctx, message['cmd'])(message['args'], message['data'])
            except Exception as e:
                traceback.print_exc()
                logging.error(f"Exception when executing command {message['cmd']}: {e}")
                result = {"error": f"Exception when executing command {message['cmd']}: {e}"}
                success = False

        except AttributeError:
            traceback.print_exc()
            logging.error(f"Context {message['cmd']} does not exist")
            result = {"error": f"Context {message['cmd']} does not exist"}

        await websocket.send(json.dumps({
                'type': 'command',
                'ctx': message['ctx'],
                'name': message['cmd'],
                'success': success,
                'result': result
        }))


async def handler(websocket, path, teamserver):
    username, _ = decode_auth_header(websocket.request_headers)
    ip, _ = websocket.remote_address

    logging.info(f"New client connected {username}@{ip}")
    await teamserver.users.register(username, websocket)
    await teamserver.update_stats()

    while True:
        try:
            msg = await asyncio.wait_for(websocket.recv(), timeout=20)
        except asyncio.TimeoutError:
            # No data in 20 seconds, check the connection.
            logging.debug(f"No data from {username}@{ip} after 20 seconds, sending ping")
            try:
                pong_waiter = await websocket.ping()
                await asyncio.wait_for(pong_waiter, timeout=10)
            except asyncio.TimeoutError:
                # No response to ping in 10 seconds, disconnect.
                logging.debug(f"No pong from {username}@{ip} after 10 seconds, closing connection")
                teamserver.users.unregister(username)
                return

        except websockets.exceptions.ConnectionClosed:
            logging.debug(f"Connection closed by client")
            teamserver.users.unregister(username)
            return

        else:
            message = json.loads(msg)
            logging.debug(f"Received message from {username}@{ip} path:{path} msg: {message}")
            await teamserver.process(websocket, message)


class STWebSocketServerProtocol(WebSocketServerProtocol):
    async def process_request(self, path, request_headers):
        try:
            username, password_digest = decode_auth_header(request_headers)
            if not hmac.compare_digest(password_digest, teamserver_digest):
                logging.error(f"User {username} failed authentication")
                return http.HTTPStatus.UNAUTHORIZED, [], b'UNAUTHORIZED\n'
        except KeyError:
            logging.error('Received handshake with no authorization header')
            return http.HTTPStatus.FORBIDDEN, [], b'FORBIDDEN\n'

        logging.info(f"User {username} authenticated successfully")


async def server(stop):
    teamserver = TeamServer()
    bound_handler = functools.partial(handler, teamserver=teamserver)
    logging.debug(f"Server started on {args['<host>']}:{args['--port']}")

    async with websockets.serve(
        bound_handler,
        host=args['<host>'],
        port=int(args['--port']),
        create_protocol=STWebSocketServerProtocol,
        ssl=None if args['--insecure'] else ssl_context
    ):
        await stop

if __name__ == '__main__':
    args = docopt(__doc__, version='0.0.1dev')
    loop = asyncio.get_event_loop()

    teamserver_digest = hmac.new(args['<password>'].encode(), msg=b'silenttrinity', digestmod=sha512).hexdigest()

    stop = asyncio.Future()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set_result, None)

    if args['--insecure']:
        logging.warning('SECURITY WARNING: --insecure flag passed, communication between client and server will be in cleartext!')

    loop.run_until_complete(server(stop))

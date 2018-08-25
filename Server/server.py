#!/usr/bin/env python3

"""
Usage: server.py <host> <password> [-h] [-v] [--port <PORT>] 
                [--insecure]

optional arguments:
    -h, --help          Show this help message and exit
    -v, --version       Show version
    -p, --port <PORT>   Port to bind to [default: 5000]
    --insecure          Connect without TLS
"""

import asyncio
import json
import logging
import ssl
import pathlib
import websockets
import signal
import http
import hashlib
from websockets import WebSocketServerProtocol
from docopt import docopt
from hmac import compare_digest

logging.basicConfig(format="%(asctime)s [%(levelname)s] - %(filename)s: %(funcName)s - %(message)s", level=logging.DEBUG)

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(
    pathlib.Path(__file__).with_name('test.pem')
)


class Events:
    def state(self, state):
        return json.dumps({'type': 'state', **state})

    def users(self, users):
        return json.dumps({'type': 'users', 'count': len(users)})


class User:
    def __init__(self, username, websocket):
        self.id = None
        self.username = username
        self.websocket = websocket
    
    async def send(self, message):
        self.websocket.send(message)
    
    async def disconnect(self):
        self.websocket.close()

    def __str__(self):
        return f"User(id='{self.id}' username='{self.username}' websocket='{self.websocket}')"

class Users:
    def __init__(self):
        self.users = set()
    
    def add_user(self, username, websocket):
        self.users.add(User(username, websocket))
    
    def remove_user(self, username):
        self.users.remove(username)

class TeamServer:
    def __init__(self):
        self.events = Events()
        self.users = Users()

    async def notify_users(self):
        message = self.events.users_event()
        await asyncio.wait([user.send(message) for user in self.users])

    async def register(self, websocket):
        self.users.add(websocket)
        await self.notify_users()

    async def unregister(self, websocket):
        self.users.remove(websocket)
        await self.notify_users()

#async def producer_handler(websocket, path):
#    while True:
#        message = await producer()
#        await websocket.send(message)

async def handler(websocket, path):
    logging.debug(f"New client connected '{websocket.remote_address}'")
    while True:
        try:
            msg = await asyncio.wait_for(websocket.recv(), timeout=20)
        except asyncio.TimeoutError:
            # No data in 20 seconds, check the connection.
            logging.debug(f"No data from '{websocket.remote_address}' after 20 seconds, sending ping")
            try:
                pong_waiter = await websocket.ping()
                await asyncio.wait_for(pong_waiter, timeout=10)
            except asyncio.TimeoutError:
                # No response to ping in 10 seconds, disconnect.
                logging.debug(f"No pong from '{websocket.remote_address}' after 10 seconds, closing connection")
                break
        else:
            logging.debug(f"Received message from '{websocket.remote_address}' path:{path} msg:{msg}")
            await websocket.send(msg)

    #producer_task = asyncio.ensure_future(producer_handler(websocket, path))

class STWebSocketServerProtocol(WebSocketServerProtocol):
    async def process_request(self, path, request_headers):
        try:
            authorization_header = request_headers['Authorization']
            if not compare_digest(authorization_header, teamserver_password):
                logging.error('Authentication failure!')
                return http.HTTPStatus.UNAUTHORIZED, [], b'UNAUTHORIZED\n'
        except KeyError:
            logging.error('Received handshake with no authorization header')
            return http.HTTPStatus.FORBIDDEN, [], b'FORBIDDEN\n'

        logging.info('Client authenticated successfully!')


async def server(stop):
    logging.debug(f"Server started on {args['<host>']}:{args['--port']}")
    async with websockets.serve(handler, host=args['<host>'], port=int(args['--port']), create_protocol=STWebSocketServerProtocol, 
                                ssl=None if args['--insecure'] else ssl_context):
        await stop


if __name__ == '__main__':
    args = docopt(__doc__, version='0.0.1dev')
    loop = asyncio.get_event_loop()

    teamserver_password = hashlib.sha512(args['<password>'].encode()).hexdigest()

    stop = asyncio.Future()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set_result, None)

    if args['--insecure']:
        logging.warning('SECURITY WARNING: --insecure flag passed, communication between client and server will be in cleartext!')

    loop.run_until_complete(server(stop))

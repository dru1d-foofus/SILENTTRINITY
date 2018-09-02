#!/usr/bin/env python3.7

"""
Usage: teamserver.py <host> <password> [-h] [-v] [--port <PORT>] 
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
import random
import functools
from websockets import WebSocketServerProtocol
from docopt import docopt
from hashlib import sha512
from hmac import compare_digest

logging.basicConfig(format="%(asctime)s [%(levelname)s] - %(filename)s: %(funcName)s - %(message)s", level=logging.DEBUG)

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(
    pathlib.Path(__file__).with_name('test.pem')
)


class User:
    def __init__(self, username, websocket):
        self.username = username
        self.websocket = websocket

    async def send(self, message):
        await self.websocket.send(message)
    
    async def disconnect(self):
        await self.websocket.close()

    def __str__(self):
        return f"User(username='{self.username}' websocket='{self.websocket}')"


class Users:
    def __init__(self):
        self.users = set()

    def add(self, username, websocket):
        self.users.add(User(username, websocket))

    def remove(self, username):
        self.users.remove(username)

    async def notify(self, message):
        message = json.dumps({'type': 'message', 'status': 'info', 'text': message})
        await asyncio.wait([user.send(message) for user in self.users])


class TeamServer:
    def __init__(self):
        self.users = Users()
        #self.listeners = Listeners()
        #self.sessions = Sessions()
        #self.events = Events()
        #self.modules = Modules()



    async def register(self, username, websocket):
        self.users.add(username, websocket)
        await self.users.notify(f"User {username} has joined!")

    def unregister(self, username):
        self.users.remove(username)
        #await self.notify()
    
    async def server(self, websocket, msg):
        await websocket.send(json.dumps({'type': 'server', 'shells': random.randint(1, 50), 'listeners': random.randint(1, 50), 'users': random.randint(1, 50)}))

    async def process(self, websocket, message):
        try:
            await getattr(self, message['cmd'])(websocket, message['args'])
        except AttributeError:
            logging.error(f"Command '{message['cmd']}' not found")


async def handler(websocket, path, teamserver):
    username, _ = websocket.request_headers['Authorization'].split(':')
    ip, _ =  websocket.remote_address

    logging.debug(f"New client connected {username}@{ip}")
    await teamserver.register(username, websocket)
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
                #teamserver.unregister(username)
                return

        except websockets.exceptions.ConnectionClosed:
            logging.debug(f"Connection closed by client")
            #teamserver.unregister(username)
            return

        else:
            message = json.loads(msg)
            logging.debug(f"Received message from {username}@{ip} path:{path} msg: {message}")
            await teamserver.process(websocket, message)


class STWebSocketServerProtocol(WebSocketServerProtocol):
    async def process_request(self, path, request_headers):
        try:
            username, password_hash = request_headers['Authorization'].split(':')
            if not compare_digest(password_hash, teamserver_password):
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
    async with websockets.serve(bound_handler, host=args['<host>'], port=int(args['--port']), 
                                create_protocol=STWebSocketServerProtocol, 
                                ssl=None if args['--insecure'] else ssl_context):
        await stop


if __name__ == '__main__':
    args = docopt(__doc__, version='0.0.1dev')
    loop = asyncio.get_event_loop()

    teamserver_password = sha512(args['<password>'].encode()).hexdigest()

    stop = asyncio.Future()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set_result, None)

    if args['--insecure']:
        logging.warning('SECURITY WARNING: --insecure flag passed, communication between client and server will be in cleartext!')

    loop.run_until_complete(server(stop))

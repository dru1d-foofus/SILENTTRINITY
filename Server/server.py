#!/usr/bin/env python3

"""

Usage: server.py <host> <password> [-h] [--port <PORT>]

optional arguments:
    -h, --help          Show this help message and exit
    -v, --version       Show version
    -p, --port <PORT>   Port to bind to [default: 5000]

"""

import asyncio
import json
import logging
import ssl
import pathlib
import websockets
import signal
from docopt import docopt
from http import HTTPStatus

logging.basicConfig(format="%(asctime)s [%(levelname)s] - %(filename)s: %(funcName)s - %(message)s", level=logging.DEBUG)


class Events:
    def state_event(self, state):
        return json.dumps({'type': 'state', **state})

    def users_event(self, users):
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
    def __init__(self, args):
        self.args = args
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
            break

    #producer_task = asyncio.ensure_future(producer_handler(websocket, path))

#ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
#ssl_context.load_cert_chain(
#    pathlib.Path(__file__).with_name('key.pem')
#)

class STWebSocketProtocol(websockets.WebSocketServerProtocol):
    async def process_request(self, path, request_headers):
        logging.debug('Hit hook')
        return None


async def server(stop, args):
    logging.debug(f"Server started on {args['<host>']}:{args['--port']}")
    async with websockets.serve(handler, host=args['<host>'], port=int(args['--port']), create_protocol=STWebSocketProtocol): # ssl=ssl_context)
        await stop


if __name__ == '__main__':
    args = docopt(__doc__, version='0.0.1dev')
    loop = asyncio.get_event_loop()

    stop = asyncio.Future()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set_result, None)

    loop.run_until_complete(server(stop, args))

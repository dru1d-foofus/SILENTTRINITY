#!/usr/bin/env python3.7

"""
Usage: silenttrinity.py <host> <username> <password> [-h] [-v] [-d] [--port <PORT>]
                        [--resource-file <FILE>] [--insecure]

optional arguments:
    -h, --help                   Show this help message and exit
    -v, --version                Show version
    -p, --port <PORT>            Teamserver port [default: 5000]
    -r, --resource-file <FILE>   Read resource file
    -d, --debug                  Enable debug output
    --insecure                   Connect without TLS
"""

import asyncio
import pathlib
import ssl
import websockets
import logging
import http
import json
import functools
import core.state as client_state
from core.commands import MainCmdLoop
from docopt import docopt
from core.utils import generate_auth_header
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.application import run_in_terminal
from core.utils import print_bad, print_good, print_info

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_context.check_hostname = False
ssl_context.load_verify_locations(
    pathlib.Path(__file__).with_name('test.pem')
)


class EventHandler:
    def __init__(self, websocket, cmdloop):
        self.cmdloop = cmdloop
        self.websocket = websocket

        asyncio.create_task(self.message_handler())

    def message(self, data):
        if data['status'] == 'info':
            print_info(data['text'])
        elif data['status'] == 'bad':
            print_bad(data['text'])
        elif data['status'] == 'good':
            print_good(data['text'])

    def server_stats(self, data):
        client_state.SESSIONS = data['sessions']
        client_state.USERS = data['users']
        client_state.LISTENERS = data['listeners']

    async def message_handler(self):
        async for message in self.websocket:
            message = json.loads(message)
            if message['type'] == 'event':
                logging.info(f'Got event from server: {message}')
                try:
                    msg_handler = functools.partial(getattr(self, message['name']), data=message['data'])
                    with patch_stdout():
                        run_in_terminal(msg_handler)
                except AttributeError:
                    logging.error(f"Got event of unknown type '{message['name']}'")

            elif message['type'] == 'command':
                ctx = self.cmdloop.get_context(message['ctx'])
                bound_cmd_handler = functools.partial(getattr(ctx, f"{message['name']}_result"), result=message['result'])
                with patch_stdout():
                    run_in_terminal(bound_cmd_handler)


async def STClient(url):
    auth_header = generate_auth_header(args['<username>'], args['<password>'])

    while True:
        try:
            logging.debug(f'Connecting to {url}')
            async with websockets.connect(url, extra_headers=auth_header, ssl=None if args['--insecure'] else ssl_context) as websocket:
                logging.debug(f'Connected to {url}')
                client_state.CONNECTED = True

                cmdloop = MainCmdLoop(websocket)
                EventHandler(websocket, cmdloop)
                asyncio.create_task(cmdloop())

                while True:
                    try:
                        pong_waiter = await websocket.ping()
                        await asyncio.wait_for(pong_waiter, timeout=10)
                    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed) as e:
                        logging.error(e)
                        logging.error("Disconnected from teamserver")
                        client_state.CONNECTED = False
                        break

                    await asyncio.sleep(10)

        except websockets.exceptions.InvalidStatusCode as e:
            logging.error(e)
            logging.error('Unable to authenticate to team server, wrong password?')
            break

        except ConnectionRefusedError as e:
            logging.error(e)
            logging.error('Error connecting to team server: connection was refused, retrying in 10 seconds')
            await asyncio.sleep(10)


if __name__ == '__main__':
    args = docopt(__doc__, version='0.0.1dev')
    url = f"{'ws' if args['--insecure'] else 'wss'}://{args['<host>']}:{args['--port']}"

    client_state.args = args
    client_state.USERNAME = args['<username>']
    client_state.HOST = args['<host>']
    client_state.PORT = args['--port']

    log_level = logging.DEBUG if args['--debug'] else logging.INFO
    logging.basicConfig(format="%(asctime)s [%(levelname)s] - %(filename)s: %(funcName)s - %(message)s", level=log_level)
    logging.getLogger('websockets').setLevel(log_level)

    if args['--insecure']:
        logging.warning('SECURITY WARNING: --insecure flag passed, comms between client and server will be in cleartext!')

    asyncio.get_event_loop().run_until_complete(STClient(url))

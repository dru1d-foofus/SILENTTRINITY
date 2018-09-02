#!/usr/bin/env python3.7

"""
Usage: client.py <host> <username> <password> [-h] [-v] [-d] [--port <PORT>]
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
import json
import http
import functools
from docopt import docopt
from shlex import split
from termcolor import colored
from hashlib import sha512
from websockets.http import Headers
from prompt_toolkit import PromptSession
from prompt_toolkit.eventloop import use_asyncio_event_loop
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.application import run_in_terminal

use_asyncio_event_loop()

completer = WordCompleter(['listeners', 'sessions', 'modules', 'options', 'events', 'users', 'server', 'exit'])

CONNECTED = False
SHELLS    = 0
USERS     = 0
LISTENERS = 0

def bottom_toolbar():
    if CONNECTED:
        return HTML(f"{args['<username>']}@{args['<host>']}:{args['--port']} (Shells: {SHELLS} Users: {USERS} Listeners: {LISTENERS})")
    else:
        return HTML(f'<b><style bg="ansired">Disconnected</style></b>')

session = PromptSession('ST > ', bottom_toolbar=bottom_toolbar, completer=completer, auto_suggest=AutoSuggestFromHistory())

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_context.check_hostname = False
ssl_context.load_verify_locations(
    pathlib.Path(__file__).with_name('test.pem')
)

def print_good(msg):
    print(f"{colored('[+]', 'green')} {msg}")


def print_bad(msg):
    print(f"{colored('[-]', 'red')} {msg}")


def print_info(msg):
    print(f"{colored('[*]', 'blue')} {msg}")


class Events:
    def __init__(self, websocket):
        self.websocket = websocket

    def message(self, msg):
        if msg['status'] == 'info':
            print_info(msg['text'])
        elif msg['status'] == 'bad':
            print_bad(msg['text'])
        if msg['status'] == 'good':
            print_good(msg['text'])

    def state(self, msg):
        global SHELLS, USERS, LISTENERS
        SHELLS = msg['shells']
        USERS  = msg['users']
        LISTENERS = msg['listeners']


async def run_resource_file(websocket):
    with open(args['--resource-file']) as resource_file:
        for cmd in resource_file:
            with patch_stdout():
                result = await session.prompt(accept_default=True, default=cmd.strip(), async_=True)
                if len(result):
                    command = split(result)
                    await websocket.send(json.dumps({"cmd": command[0], "args": command[1:]}))


async def handler(websocket, events):
    async for message in websocket:
        message = json.loads(message)
        logging.debug(f'Got message from server: {message}')
        msg_handler = functools.partial(getattr(events, message['type']), msg=message)
        with patch_stdout():
            run_in_terminal(msg_handler)


async def cmdloop(websocket):
    global CONNECTED
    if args['--resource-file'] and pathlib.Path(args['--resource-file']).exists():
        await asyncio.ensure_future(run_resource_file(websocket))
    else:
        logging.error('Error reading resource file')

    while True:
        with patch_stdout():
            result = await session.prompt(async_=True)
            if result == 'exit':
                websocket.close()
                return
            elif len(result):
                command = split(result)
                try:
                    await websocket.send(json.dumps({"cmd": command[0], "args": command[1:]}))
                except websockets.exceptions.ConnectionClosed as e:
                    logging.error(e)
                    logging.error("Disconnected from teamserver")
                    CONNECTED = False

async def STClient(url):
    global CONNECTED
    auth_header = Headers({'Authorization': f"{args['<username>']}:{sha512(args['<password>'].encode()).hexdigest()}"})
    cmdloop_future = None
    msg_handler_future = None

    while True:
        try:
            logging.debug(f'Connecting to {url}')
            async with websockets.connect(url, extra_headers=auth_header, ssl=None if args['--insecure'] else ssl_context) as websocket:
                logging.debug(f'Connected to {url}')
                CONNECTED = True

                events              = Events(websocket)
                msg_handler_future  = asyncio.ensure_future(handler(websocket, events))
                #erver_pinger_future = asyncio.ensure_future(server_pinger(websocket))
                cmdloop_future      = asyncio.ensure_future(cmdloop(websocket))

                while True:
                    try:
                        pong_waiter = await websocket.ping()
                        await asyncio.wait_for(pong_waiter, timeout=10)
                    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed) as e:
                        logging.error(e)
                        logging.error("Disconnected from teamserver")
                        CONNECTED = False
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

    log_level = logging.DEBUG if args['--debug'] else logging.INFO
    logging.basicConfig(format="%(asctime)s [%(levelname)s] - %(filename)s: %(funcName)s - %(message)s", level=log_level)
    logging.getLogger('websockets').setLevel(log_level)

    if args['--insecure']:
        logging.warning('SECURITY WARNING: --insecure flag passed, communication between client and server will be in cleartext!')

    asyncio.get_event_loop().run_until_complete(STClient(url))

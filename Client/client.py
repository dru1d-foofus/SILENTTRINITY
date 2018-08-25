#!/usr/bin/env python3

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
import hashlib
import functools
from docopt import docopt
from shlex import split
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

completer = WordCompleter(['listeners', 'sessions', 'modules', 'events', 'users', 'exit'])

def bottom_toolbar():
    shells = 0
    users = 0
    listeners = 0
    return HTML(f'Shells: {shells} Users: {users} Listeners: {listeners}')

session = PromptSession('ST > ', completer=completer, auto_suggest=AutoSuggestFromHistory(),
                        bottom_toolbar=bottom_toolbar)

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_context.check_hostname = False
ssl_context.load_verify_locations(
    pathlib.Path(__file__).with_name('test.pem')
)

async def run_resource_file(websocket):
    with open(args['--resource-file']) as resource_file:
        for cmd in resource_file:
            with patch_stdout():
                result = await session.prompt(async_=True, accept_default=True, default=cmd.strip())
                if len(result):
                    command = split(result)
                    await websocket.send(json.dumps({"cmd": command[0], "args": command[1:]}))


async def handler(websocket):
    async for msg in websocket:
        logging.debug(f'Got message from server: {msg}')


async def cmdloop(url):
    logging.debug(f'Connecting to {url}')
    auth_header = Headers({'Authorization': hashlib.sha512(args['<password>'].encode()).hexdigest()})

    try:
        async with websockets.connect(url, extra_headers=auth_header, ssl=None if args['--insecure'] else ssl_context) as websocket:
            logging.debug('Connected')
            asyncio.ensure_future(handler(websocket))

            if args['--resource-file'] and pathlib.Path(args['--resource-file']).exists():
                await asyncio.ensure_future(run_resource_file(websocket))
            else:
                logging.error('Error reading resource file')

            while True:
                with patch_stdout():
                    result = await session.prompt(async_=True)
                    if result == 'exit':
                        return
                    elif len(result):
                        command = split(result)
                        await websocket.send(json.dumps({"cmd": command[0], "args": command[1:]}))

    except websockets.exceptions.InvalidStatusCode as e:
        logging.error(e)
        logging.error('Unable to authenticate to team server, wrong password?')

if __name__ == '__main__':
    args = docopt(__doc__, version='0.0.1dev')
    url = f"{'ws' if args['--insecure'] else 'wss'}://{args['<host>']}:{args['--port']}"

    log_level = logging.DEBUG if args['--debug'] else logging.INFO
    logging.basicConfig(format="%(asctime)s [%(levelname)s] - %(filename)s: %(funcName)s - %(message)s", level=log_level)
    logging.getLogger('websockets').setLevel(log_level)

    if args['--insecure']:
        logging.warning('SECURITY WARNING: --insecure flag passed, communication between client and server will be in cleartext!')

    asyncio.get_event_loop().run_until_complete(cmdloop(url))

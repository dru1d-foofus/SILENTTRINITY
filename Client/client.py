#!/usr/bin/env python3

"""
Usage: client.py <host> <username> <password> [-h] [--port <PORT>]
                 [--insecure]

optional arguments:
    -h, --help          Show this help message and exit
    -v, --version       Show version
    -p, --port <PORT>   Teamserver port [default: 5000]
    --insecure          Connect without TLS

"""
import asyncio
import pathlib
import ssl
import websockets
import logging
from docopt import docopt

logging.basicConfig(format="%(asctime)s [%(levelname)s] - %(filename)s: %(funcName)s - %(message)s", level=logging.DEBUG)

#ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
#ssl_context.load_verify_locations(
#    pathlib.Path(__file__).with_name('localhost.pem'))

async def handler(url):
    logging.debug(f'Connecting to {url}')
    async with websockets.connect(url) as websocket:
        logging.debug('Connected')
        async for msg in websocket:
            logging.debug(f'Got message from server: {msg}')

if __name__ == '__main__':
    args = docopt(__doc__, version='0.0.1dev')

    url = f"ws://{args['<host>']}:{args['--port']}"

    asyncio.get_event_loop().run_until_complete(handler(url))

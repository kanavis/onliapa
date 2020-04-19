#!/usr/bin/env python

import argparse
import asyncio
import logging
import sys
from functools import partial

import websockets

from persister.persister import Persister
from server.server import serve

log = logging.getLogger('onliapa')

parser = argparse.ArgumentParser(description='Run server')
parser.add_argument('-l', '--listen-host', help='IP', default='127.0.0.1')
parser.add_argument('-p', '--listen-port', type=int, help='port', default=6613)
parser.add_argument('-r', '--redis-url', type=str, help='redis url',
                    default='redis://localhost')
parser.add_argument('-d', '--debug', action='store_true')
args = parser.parse_args()

# Logging
log_level = logging.DEBUG if args.debug else logging.INFO
log.setLevel(log_level)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setLevel(log_level)
formatter = logging.Formatter(
    '%(asctime)s [%(module)s] %(levelname)s - %(message)s',
)
handler.setFormatter(formatter)
log.addHandler(handler)

# Persister
persister = Persister(args.redis_url)

# Server
serve_ = partial(serve, persister)


async def start_server():
    try:
        await persister.ping()
        log.info('Connected to redis')
    except OSError as err:
        log.critical(f'Failed to connect to redis: {err}')
        sys.exit(1)
    try:
        await websockets.serve(serve_, args.listen_host, args.listen_port)
        log.info(f'Server is listening {args.listen_host}:{args.listen_port}')
    except OSError as err:
        log.critical(f'Failed to start server: {err}')
        sys.exit(1)

asyncio.get_event_loop().run_until_complete(start_server())

try:
    asyncio.get_event_loop().run_forever()
except KeyboardInterrupt:
    print('Killed')

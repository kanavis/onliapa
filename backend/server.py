#!/usr/bin/env python

import argparse
import asyncio
import logging
import sys

import websockets
from server.server import serve

log = logging.getLogger('onliapa')

parser = argparse.ArgumentParser(description='Run server')
parser.add_argument('-l', '--listen-host', help='IP', default='127.0.0.1')
parser.add_argument('-p', '--listen-port', type=int, help='port', default=6613)
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

# Server
start_server = websockets.serve(serve, args.listen_host, args.listen_port)

try:
    asyncio.get_event_loop().run_until_complete(start_server)
except OSError as err:
    log.critical(f'Failed to start server: {err}')
    sys.exit(1)

log.info(f'Server is listening on {args.listen_host}:{args.listen_port}')
try:
    asyncio.get_event_loop().run_forever()
except KeyboardInterrupt:
    print('Killed')

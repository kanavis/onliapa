#!/usr/bin/env python

import asyncio
import sys
import websockets
from onliapa.server.protocol import rmsg


async def connect():
    uri = "ws://localhost:6613/ws/game/" + sys.argv[2]
    async with websockets.connect(uri) as websocket:
        await websocket.send(rmsg('user-auth', {'user_name': 'anus'}))
        while True:
            res = await(websocket.recv())
            print(res)


async def create():
    uri = "ws://localhost:6613/ws/new_game/"
    async with websockets.connect(uri) as websocket:
        await websocket.send(
            rmsg('new-game', {'round_length': 30, 'hat_words_per_user': 5}))
        res = await(websocket.recv())
        print(res)

asyncio.get_event_loop().run_until_complete(globals()[sys.argv[1]]())

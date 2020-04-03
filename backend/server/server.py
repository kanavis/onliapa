import logging
import re

from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed

from server.room import rooms
from server.protocol import rerr

log = logging.getLogger('onliapa.server.server')


class Matcher:
    def __init__(self, regex):
        self.matches = None
        self.regex = regex

    def match(self, value):
        self.matches = self.regex.search(value)
        return self.matches


RE_GAME_PATH = Matcher(re.compile(r'^/ws/game/([A-Za-z0-9]{8})/?$'))
RE_ADMIN_PATH = Matcher(re.compile(r'^/ws/admin/([A-Za-z0-9]{8})/?$'))


async def serve_game(ws: WebSocketServerProtocol, game_id: str, admin: bool):
    ip = ws.remote_address
    try:
        try:
            room = rooms[game_id]
        except KeyError:
            log.info(f'{ip} is trying to join non-existent game {game_id}')
            await ws.send(rerr('wrong-game'))
            await ws.close()
            return
        if admin:
            await room.serve_admin(ws)
        else:
            await room.serve_user(ws)
    except ConnectionClosed:
        log.info(f'Host {ip} closed the connection')


async def _serve(ws: WebSocketServerProtocol, path: str):
    if RE_GAME_PATH.match(path):
        game_id = RE_GAME_PATH.matches.group(1)
        log.info(f'New connection from {ws.remote_address} to game {game_id}')
        await serve_game(ws, game_id, False)
    elif RE_ADMIN_PATH.match(path):
        game_id = RE_GAME_PATH.matches.group(1)
        log.info(f'New admin conn from {ws.remote_address} to game {game_id}')
        await serve_game(ws, game_id, True)
    else:
        await ws.close(1002, 'Wrong path')


async def serve(ws: WebSocketServerProtocol, path: str):
    # noinspection PyBroadException
    try:
        await _serve(ws, path)
    except Exception:
        log.exception(f'Exception in handle {ws.remote_address} path {path}')

import logging
import random
import re

from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed

from game.game import Game
from server.errors import ProtocolError
from server.messages import NewGameRequest
from server.room import rooms
from server.protocol import rerr, recv_d, rmsg

log = logging.getLogger('onliapa.server.server')


class Matcher:
    def __init__(self, regex):
        self.matches = None
        self.regex = regex

    def match(self, value):
        self.matches = self.regex.search(value)
        return self.matches


RE_NEW_GAME_PATH = Matcher(re.compile(r'^/ws/new_game/?$'))
RE_GAME_PATH = Matcher(re.compile(r'^/ws/game/([A-Za-z0-9]{8})/?$'))
RE_ADMIN_PATH = Matcher(re.compile(r'^/ws/admin/([A-Za-z0-9]{8})/?$'))
GAME_ID_LETTERS = 'abcdefghijklmnopqrstuvwxyz0123456789'
GAME_ID_LEN = 8


async def serve_game(ws: WebSocketServerProtocol, game_id: str, admin: bool):
    ip = ':'.join(map(str, ws.remote_address))
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
    await ws.close()


def new_game_id() -> str:
    while True:
        game_id = ''.join(
            random.choice(GAME_ID_LETTERS)
            for _ in range(GAME_ID_LEN)
        )
        if game_id not in rooms:
            return game_id


async def create_game(ws: WebSocketServerProtocol):
    ip = ':'.join(map(str, ws.remote_address))
    request: NewGameRequest = await recv_d(ws, NewGameRequest, 'new-game')

    game_id = new_game_id()
    game = Game(
        game_id=game_id,
        game_name=request.game_name,
        round_length=request.round_length,
        hat_words_per_user=request.hat_words_per_user,
    )
    rooms[game_id] = game.room
    log.info(f'Created game {game_id} named \"{request.game_name}\" for {ip}')
    await ws.send(rmsg('new-game-id', game_id))


async def _serve(ws: WebSocketServerProtocol, path: str):
    if RE_GAME_PATH.match(path):
        game_id = RE_GAME_PATH.matches.group(1)
        log.info(f'New connection from {ws.remote_address} to game {game_id}')
        await serve_game(ws, game_id, False)
    elif RE_ADMIN_PATH.match(path):
        game_id = RE_GAME_PATH.matches.group(1)
        log.info(f'New admin conn from {ws.remote_address} to game {game_id}')
        await serve_game(ws, game_id, True)
    elif RE_NEW_GAME_PATH.match(path):
        log.info(f'New game request from {ws.remote_address}')
        await create_game(ws)
    else:
        await ws.close(1002, f'Wrong path {path}')


async def serve(ws: WebSocketServerProtocol, path: str):
    ip = ws.remote_address
    try:
        await _serve(ws, path)
    except ConnectionClosed:
        log.info(f'Host {ip} closed the connection')
    except ProtocolError as err:
        log.info(f'Host {ip}: protocol error: {err}')
        try:
            await ws.close(1002, f'protocol error')
        except Exception as err:
            log.debug(f'Host {ip}: Error closing failed socket: {err}')
            pass
    except Exception:
        log.exception(f'Exception in handle {ws.remote_address} path {path}')

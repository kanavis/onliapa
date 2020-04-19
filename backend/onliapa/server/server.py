import logging
import random
import re

from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed

from onliapa.game.game import Game
from onliapa.persister import persister
from onliapa.server.errors import ProtocolError
from onliapa.server.helpers import remote_addr
from onliapa.server.messages import NewGameRequest
from onliapa.server.room import rooms
from onliapa.server.protocol import rerr, recv_d, rmsg

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


async def serve_game(
    ws: WebSocketServerProtocol,
    game_id: str,
    admin: bool,
    pr: persister.Persister
):
    ip = remote_addr(ws)
    try:
        room = rooms[game_id]
    except KeyError:
        try:
            game = await load_game(game_id=game_id, pr=pr)
            rooms[game_id] = game.room
            room = rooms[game_id]
            log.info(f'Loaded game {game_id} from persister')
        except persister.GameDoesNotExist:
            log.info(f'{ip} is trying to join non-existent game {game_id}')
            await ws.send(rerr('wrong-game', 'Wrong game'))
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


def make_state_saver(game_id: str, pr: persister.Persister):
    async def state_saver(state: str):
        try:
            await pr.save_game(game_id, state=state)
            log.debug(f'Written game {game_id} state')
        except persister.CommunicationError as err:
            log.error(f'Error while saving game {game_id}: {err}')
    return state_saver


async def create_game(ws: WebSocketServerProtocol, pr: persister.Persister):
    ip = remote_addr(ws)
    request: NewGameRequest = await recv_d(ws, NewGameRequest, 'new-game')

    game_id = new_game_id()

    game = Game(
        game_id=game_id,
        game_name=request.game_name,
        round_length=request.round_length,
        hat_words_per_user=request.hat_words_per_user,
        state_saver=make_state_saver(game_id=game_id, pr=pr),
    )
    rooms[game_id] = game.room
    log.info(f'Created game {game_id} named \"{request.game_name}\" for {ip}')
    await ws.send(rmsg('new-game-id', game_id))


async def load_game(game_id: str, pr: persister.Persister) -> Game:
    state = await pr.load_game(game_id)
    try:
        return Game.load_state(state, make_state_saver(game_id=game_id, pr=pr))
    except (ValueError, KeyError, TypeError) as err:
        cls_name = err.__class__.__name__
        log.error(f'Error loading game {game_id}: {cls_name} {err}. Clearing')
        await pr.del_game(game_id)
        raise persister.GameDoesNotExist()


async def _serve(
    pr: persister.Persister,
    ws: WebSocketServerProtocol,
    path: str
):
    ip = remote_addr(ws)
    if RE_GAME_PATH.match(path):
        game_id = RE_GAME_PATH.matches.group(1)
        log.info(f'New connection from {ip} to game {game_id}')
        await serve_game(ws, game_id, False, pr)
    elif RE_ADMIN_PATH.match(path):
        game_id = RE_ADMIN_PATH.matches.group(1)
        log.info(f'New admin connection from {ip} to game {game_id}')
        await serve_game(ws, game_id, True, pr)
    elif RE_NEW_GAME_PATH.match(path):
        log.info(f'New game session connection from {ip}')
        await create_game(ws, pr)
    else:
        await ws.send(rerr('wrong-path', 'Wrong path'))
        await ws.close(1002, f'Wrong path {path}')


async def serve(
    pr: persister.Persister,
    ws: WebSocketServerProtocol,
    path: str,
):
    ip = remote_addr(ws)
    try:
        await _serve(pr=pr, ws=ws, path=path)
    except ConnectionClosed as err:
        log.info(f'Connection {ip} closed ({err.code})')
    except ProtocolError as err:
        log.info(f'Connection {ip}: protocol error: {err}')
        try:
            await ws.send(rerr('protocol-error', 'Protocol error'))
            await ws.close(1002, f'protocol error')
        except Exception as err:
            log.debug(f'Connection {ip}: Error closing failed socket: {err}')
            pass
    except Exception as err:
        log.exception(f'Exception in handle {ip} path {path}')

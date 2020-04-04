import logging
from typing import Optional

from websockets import WebSocketServerProtocol

from server.errors import ProtocolError
from server.messages import AuthRequest
from server.protocol import recv, rerr, rmsg

log = logging.getLogger('onliapa.server.auth')


class User:
    user_id: int
    name: str

    def __init__(self, id_, name):
        self.user_id = id_
        self.name = name

    def __str__(self):
        return self.name

    def serialize(self):
        return {
            'user_id': self.user_id,
            'name': self.name,
        }


async def auth(websocket: WebSocketServerProtocol) -> Optional[User]:
    ip = ':'.join(map(str, websocket.remote_address))
    try:
        tag, msg = await recv(websocket, AuthRequest)
    except ProtocolError as err:
        log.info(f'Remote socket {ip} failed to authenticate: {err}')
        return None
    user_name = msg.user_name
    if user_name == 'admin':
        await websocket.send(rerr('auth-error', f'wrong name {user_name}'))
        return None

    await websocket.send(rmsg('auth-ok', ''))
    user = User(hash(user_name), user_name)
    log.info(f'Connection {ip} authenticated as {user}')

    return user
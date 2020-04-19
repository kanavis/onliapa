import logging
from typing import Optional
from zlib import adler32

from websockets import WebSocketServerProtocol

from onliapa.server.errors import ProtocolError
from onliapa.server import messages as msg
from onliapa.server.protocol import recv, rerr, rmsg

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

    @classmethod
    def deserialize(cls, state: dict) -> 'User':
        return cls(
            id_=state['user_id'],
            name=state['name'],
        )

    def to_msg(self):
        return msg.AuthUser(user_id=self.user_id, user_name=self.name)


async def auth(websocket: WebSocketServerProtocol) -> Optional[User]:
    ip = ':'.join(map(str, websocket.remote_address))
    try:
        tag, message = await recv(websocket, msg.AuthRequest)
    except ProtocolError as err:
        log.info(f'Remote socket {ip} failed to authenticate: {err}')
        return None
    user_name = message.user_name
    if user_name == 'admin':
        await websocket.send(rerr('auth-error', f'wrong name {user_name}'))
        return None

    user_id = adler32(user_name.encode())
    user = User(user_id, user_name)
    await websocket.send(rmsg('auth-ok', user.to_msg()))
    log.info(f'Connection {ip} authenticated as {user}')

    return user

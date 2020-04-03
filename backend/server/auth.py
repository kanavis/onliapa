import logging

from websockets import WebSocketServerProtocol, ProtocolError

from server.messages import AuthRequest
from server.protocol import recv, rerr

log = logging.getLogger('onliapa.server.auth')


async def auth(websocket: WebSocketServerProtocol):
    try:
        tag, msg = await recv(websocket, AuthRequest)
    except ProtocolError as err:
        log.info(f'Remote socket failed to authenticate: {err}')
        return None
    if msg.username.lower() == 'admin':
        rerr('auth-error', f'cannot use name {msg.username}')
    return msg.username

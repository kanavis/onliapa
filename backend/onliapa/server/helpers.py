""" Helpers """
from websockets import WebSocketServerProtocol

fwd_permitted = True


def remote_addr(ws: WebSocketServerProtocol):
    parts = []
    try:
        if not fwd_permitted:
            raise KeyError()
        parts.append(ws.request_headers['X-Forwarded-For'])
    except KeyError:
        try:
            parts.append(ws.remote_address[0])
        except TypeError:
            parts.append(ws.remote_address)
    try:
        parts.append(ws.remote_address[1])
    except (TypeError, IndexError):
        pass

    return ':'.join(map(str, ws.remote_address))

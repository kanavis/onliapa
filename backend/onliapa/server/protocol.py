import json
import logging
from typing import Type, Optional, Union, TypeVar, Tuple

from marshmallow import ValidationError, Schema
from websockets import WebSocketServerProtocol

from onliapa.server.errors import BaseError, ProtocolError, RemoteError

T = TypeVar('T')
log = logging.getLogger('onliapa.server.protocol')


def transcode(value, _level=0):
    if _level > 100:
        raise RecursionError(f'Level {_level} reached with {value}')
    _level += 1
    if isinstance(value, tuple) and hasattr(value, '_asdict'):
        return transcode(getattr(value, '_asdict')(), _level)
    if isinstance(value, dict):
        return {k: transcode(v, _level) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [transcode(v, _level) for v in value]
    else:
        return value


def rmsg(tag, message) -> str:
    return json.dumps({'tag': tag, 'message': transcode(message)})


def rerr(tag, message='', data=None) -> str:
    return json.dumps(
        {
            'tag': tag,
            'error': message,
            'data': data,
        },
    )


def trunc(s: str, ln: int = 100):
    if len(s) > ln:
        return f'{s[: ln]}...'
    return s


class DecodeError(BaseError):
    pass


async def recv_d(
        websocket: WebSocketServerProtocol,
        expected: Type[T],
        expected_tag: str,
):
    _, res = await recv(websocket, expected, expected_tag)
    assert isinstance(res, expected.t)
    return res


async def recv(
        websocket: WebSocketServerProtocol,
        expected: Optional[Type[T]] = None,
        expected_tag: str = None,
) -> Tuple[str, Union[T, dict, str]]:
    data = await websocket.recv()
    try:
        try:
            decoded_json = json.loads(data)
        except json.JSONDecodeError as err:
            raise DecodeError(err)
        if 'tag' not in decoded_json:
            raise DecodeError('No tag field')
        tag = decoded_json['tag']
        if expected_tag is not None:
            if tag != expected_tag:
                raise DecodeError(f'Unexpected tag: {tag} != e {expected_tag}')
        if 'message' in decoded_json:
            message = decoded_json['message']
        elif 'error' in decoded_json:
            if 'data' not in decoded_json:
                raise DecodeError('No data in error')
            raise RemoteError(tag, decoded_json['error'], decoded_json['data'])
        else:
            raise DecodeError('No error or message in data')
        if expected is not None:
            try:
                decoded = expected(**message)
            except (TypeError, ValueError, ValidationError) as err:
                raise DecodeError(f'{expected}: {err}')
            return tag, decoded
        else:
            if not isinstance(message, (dict, str)):
                raise DecodeError(f'Wrong message type {type(message)}')
            return tag, message
    except DecodeError as err:
        trunc(data)
        log.debug(
            f'Error decoding remote packet {data}'
            f'from {websocket.remote_address}: {err}',
        )
        raise ProtocolError(err, data)


class MessageType:
    def __init__(self, t):
        self.t = t
        self.name = t.__name__

    def __call__(self, **kwargs):
        if hasattr(self.t, 'Schema'):
            schema: Schema = getattr(self.t, 'Schema')()
            data = schema.load(kwargs)
        else:
            data = kwargs
        return self.t(**data)

    def __str__(self):
        return self.name


def message_type(outer):
    return MessageType(outer)

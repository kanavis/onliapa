import logging
from collections import defaultdict
from itertools import chain
from typing import Dict, Optional, Callable, Awaitable, TypeVar, Type

from marshmallow import ValidationError
from websockets import WebSocketServerProtocol, ConnectionClosed

from server.auth import auth
from server.errors import ProtocolError, RemoteError
from server.protocol import rerr, recv, trunc

log = logging.getLogger('onliapa.server.room')
T = TypeVar('T')


class GameRoom:
    users: Dict[str, WebSocketServerProtocol]
    admin: Optional[WebSocketServerProtocol]
    game_id: str

    def __init__(
            self,
            game_id: str,
            admin: Optional[WebSocketServerProtocol],
    ):
        self.users = {}
        self.admin = admin
        self.game_id = game_id
        self._subscriptions = defaultdict(list)
        self._message_subscriptions = {}
        self.subscribe('message', self._on_message)

    @staticmethod
    async def _endup_socket(socket: WebSocketServerProtocol):
        try:
            await socket.send(rerr('another-connection'))
            await socket.close()
        except ConnectionClosed:
            return

    async def subscribe(self, event, callback):
        self._subscriptions[event].append(callback)

    async def emit(self, event, data):
        for callback in self._subscriptions[event]:
            await callback(data)

    def subscribe_message(
            self,
            message: str,
            expect_type: Type[T],
            callback: Callable[[T, str], Awaitable[None]],
    ):
        if message in self._message_subscriptions:
            raise ValueError(f'Re-subscribing to message {message}')
        self._message_subscriptions[message] = (expect_type, callback)

    def message_handler(self, message: str, expect_type):
        def decorate(outer):
            self.subscribe_message(message, expect_type, outer)
            return outer
        return decorate

    async def _on_message(self, data):
        message, message_data, user = data
        try:
            expect_type, callback = self._message_subscriptions[message]
        except KeyError:
            log.warning(f'Received message without subscription: {message}')
            return
        try:
            parsed = callback(expect_type(**message_data))
        except (ValueError, TypeError, ValidationError) as err:
            log.warning(f'Failed to parse {message} message: {err}')
            return
        if user is None:
            await callback(parsed)
        else:
            await callback(parsed, user)

    async def serve_user(self, websocket: WebSocketServerProtocol):
        user = await auth(websocket)
        if user is None:
            return
        try:
            old_user = self.users[user]
        except KeyError:
            old_user = None
        self.users[user] = websocket
        await self.emit('join', user)
        if old_user:
            await self._endup_socket(self.users[user])
        while True:
            try:
                tag, data = await recv(websocket)
            except ProtocolError as err:
                log.info(f'Unreadable packet from user {user}: {err}')
                continue
            except RemoteError as err:
                log.info(f'Remote error from user {user}: {err}')
                continue
            except ConnectionClosed:
                del self.users[user]
                await self.emit('leave', user)
                raise
            await self.emit('message', (tag, data, user))

    async def serve_admin(self, websocket: WebSocketServerProtocol):
        old_admin = self.admin
        self.admin = websocket
        if old_admin:
            await self._endup_socket(self.admin)
        await self.emit('admin-join', None)
        while True:
            try:
                tag, data = await recv(websocket)
            except ProtocolError as err:
                log.info(f'Unreadable packet from admin: {err}')
                continue
            except RemoteError as err:
                log.info(f'Remote error from admin: {err}')
                continue
            except ConnectionClosed:
                self.admin = None
                await self.emit('admin-leave', None)
                raise
            await self.emit('message', (f'admin-{tag}', data, 'admin'))

    async def broadcast(self, data: str, with_admin: bool = True):
        _d = trunc(data)
        log.debug(f'Broadcasting message {_d}')
        for name, sock in (
                chain(self.users.items(), ('admin', self.admin))
                if with_admin else self.users.values()
        ):
            log.debug(f'Broadcast to {name} message {_d}')
            if sock is not None:
                try:
                    await sock.send(data)
                except ConnectionClosed:
                    pass

    async def user_send(self, user: str, data: str) -> bool:
        if user == 'admin':
            return await self.admin_send(data)
        log.debug(f'Sending to {user} message {trunc(data)}')
        if user in self.users:
            try:
                await self.users[user].send(data)
            except ConnectionClosed:
                del self.users[user]
                log.info(f'{self.game_id}: user {user} closed connection')
                return False
            return True
        else:
            return False

    async def admin_send(self, data: str) -> bool:
        log.debug(f'Sending to admin message {trunc(data)}')
        if self.admin is None:
            return False
        try:
            await self.admin.send(data)
        except ConnectionClosed:
            self.admin = None
            log.info(f'{self.game_id}: admin closed connection')
            return False
        return True


rooms: Dict[str, GameRoom] = {}

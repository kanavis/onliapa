import logging
from collections import defaultdict
from itertools import chain
from typing import Dict, Optional, Callable, Awaitable, TypeVar, Type, Any

from marshmallow import ValidationError
from websockets import WebSocketServerProtocol, ConnectionClosed

from server.auth import auth, User
from server.errors import ProtocolError, RemoteError
from server.protocol import rerr, recv, trunc

log = logging.getLogger('onliapa.server.room')
T = TypeVar('T')


class EventHandler:
    def __init__(self):
        self._subscriptions = defaultdict(list)
        self._message_subscriptions = {}
        self.subscribe('message', self._on_message)

    def subscribe_message(
            self,
            message: str,
            expect_type: Type[T],
            callback: Callable[[T, User], Awaitable[None]],
    ):
        if message in self._message_subscriptions:
            raise ValueError(f'Re-subscribing to message {message}')
        self._message_subscriptions[message] = (expect_type, callback)

    def message_handler(self, message: str, expect_type):
        def decorate(outer: Callable[[Any, T, User], Awaitable[None]]):
            self.subscribe_message(message, expect_type, outer)
            return outer

        return decorate

    async def _on_message(self, instance, data):
        message, message_data, user, socket = data
        try:
            expect_type, callback = self._message_subscriptions[message]
        except KeyError:
            log.warning(
                f'Received message without subscription: {message}')
            return
        try:
            parsed = callback(expect_type(**message_data))
        except (ValueError, TypeError, ValidationError) as err:
            log.warning(f'Failed to parse {message} message: {err}')
            return
        if user is None:
            await callback(instance, parsed, socket)
        else:
            await callback(instance, parsed, user, socket)

    def handler(self, event: str):
        def decorate(outer: Callable[[Any, Any], Awaitable[None]]):
            self.subscribe(event, outer)
            return outer

        return decorate

    def subscribe(self, event, callback):
        self._subscriptions[event].append(callback)

    async def emit(self, instance, event, data):
        for callback in self._subscriptions[event]:
            await callback(instance, data)


class EventEmitter:
    def __init__(self, handler: EventHandler, instance):
        self.instance = instance
        self.handler = handler

    async def emit(self, event, data):
        await self.handler.emit(self.instance, event, data)


class GameRoom:
    users: Dict[int, WebSocketServerProtocol]
    admin: Optional[WebSocketServerProtocol]
    game_id: str

    def __init__(
            self,
            game_id: str,
            emitter: EventEmitter,
            admin: Optional[WebSocketServerProtocol] = None,
    ):
        self.user_names = {}
        self.users = {}
        self.admin = admin
        self.game_id = game_id
        self._emitter = emitter

    def _info(self, message):
        log.info(f'Game {self.game_id}: {message}')

    def _debug(self, message):
        log.debug(f'Game {self.game_id}: {message}')

    @staticmethod
    async def _endup_socket(socket: WebSocketServerProtocol):
        try:
            await socket.send(rerr('another-connection'))
            await socket.close()
        except ConnectionClosed:
            return

    async def serve_user(self, websocket: WebSocketServerProtocol):
        user = await auth(websocket)
        if user is None:
            return
        try:
            old_user = self.users[user.user_id]
        except KeyError:
            old_user = None
        self.users[user.user_id] = websocket
        self.user_names[user.user_id] = user.name
        await self._emitter.emit('join', user)
        if old_user:
            await self._endup_socket(self.users[user.user_id])
        while True:
            try:
                tag, data = await recv(websocket)
            except ProtocolError as err:
                self._info(f'Unreadable packet from user {user}: {err}')
                continue
            except RemoteError as err:
                self._info(f'Remote error from user {user}: {err}')
                continue
            except ConnectionClosed:
                del self.users[user.user_id]
                await self._emitter.emit('leave', user)
                raise
            self._debug(f'Received message {tag} from {user}: {trunc(data)}')
            await self._emitter.emit('message', (tag, data, user, websocket))

    async def serve_admin(self, websocket: WebSocketServerProtocol):
        old_admin = self.admin
        self.admin = websocket
        if old_admin:
            await self._endup_socket(self.admin)
        await self._emitter.emit('admin-join', None)
        while True:
            try:
                tag, data = await recv(websocket)
            except ProtocolError as err:
                self._info(f'Unreadable packet from admin: {err}')
                continue
            except RemoteError as err:
                self._info(f'Remote error from admin: {err}')
                continue
            except ConnectionClosed:
                self.admin = None
                await self._emitter.emit('admin-leave', None)
                raise
            await self._emitter.emit(
                'message',
                (f'admin-{tag}', data, 'admin', websocket)
            )

    async def broadcast(self, data: str, with_admin: bool = True):
        _d = trunc(data)
        self._debug(f'Broadcasting message {_d}')
        all_users = (
            chain(self.users.items(), (('admin', self.admin),))
            if with_admin and self.admin is not None else self.users.items()
        )
        for user_id, sock in all_users:
            self._debug(f'Broadcast to {self.user_names[user_id]} message {_d}')
            if sock is not None:
                try:
                    await sock.send(data)
                except ConnectionClosed:
                    pass

    async def user_send_sock(
            self,
            user_id: int,
            sock: WebSocketServerProtocol,
            data: str) -> bool:
        user_name = self.user_names[user_id]
        self._debug(f'Sending to {user_name} message {trunc(data)}')
        try:
            await sock.send(data)
        except ConnectionClosed:
            del self.users[user_id]
            self._info(f'User {user_id} closed connection')
            return False
        return True

    async def user_send(self, user_id: int, data: str) -> bool:
        if user_id in self.users:
            sock = self.users[user_id]
            return await self.user_send_sock(user_id, sock, data)
        else:
            user_name = self.user_names[user_id]
            self._debug(f'Cannot send message to {user_name}: no socket')
            return False

    async def admin_send_sock(
            self, sock: WebSocketServerProtocol, data: str) -> bool:
        self._debug(f'Sending to admin message {trunc(data)}')
        try:
            await sock.send(data)
        except ConnectionClosed:
            self.admin = None
            self._info(f'Admin closed connection')
            return False
        return True

    async def admin_send(self, data: str) -> bool:
        if self.admin is None:
            return False
        else:
            return await self.admin_send_sock(self.admin, data)


rooms: Dict[str, GameRoom] = dict()

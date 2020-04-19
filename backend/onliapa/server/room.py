import logging
from collections import defaultdict
from itertools import chain
from typing import Dict, Optional, Callable, Awaitable, TypeVar, Type, Any, \
    Set, Iterable, Tuple

from marshmallow import ValidationError
from websockets import WebSocketServerProtocol, ConnectionClosed

from onliapa.server.auth import auth, User
from onliapa.server.errors import ProtocolError, RemoteError
from onliapa.server.protocol import recv, trunc, rerr

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
        def decorate(
                outer: Callable[
                    [Any, T, User, WebSocketServerProtocol],
                    Awaitable[None]
                ],
        ):
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
            parsed = expect_type(**message_data)
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
    users: Dict[int, Set[WebSocketServerProtocol]]
    admin: Set[WebSocketServerProtocol]
    game_id: str

    def __init__(
            self,
            game_id: str,
            emitter: EventEmitter,
            admin: Optional[WebSocketServerProtocol] = None,
    ):
        self.user_names = {}
        self.users = defaultdict(set)
        self.admin = set()
        if admin:
            self.admin.add(admin)
        self.game_id = game_id
        self._emitter = emitter

    @staticmethod
    def _wsfmt(ws: WebSocketServerProtocol):
        return ':'.join(map(str, ws.remote_address))

    def _info(self, message):
        log.info(f'Game {self.game_id}: {message}')

    def _debug(self, message):
        log.debug(f'Game {self.game_id}: {message}')

    async def serve_user(self, websocket: WebSocketServerProtocol):
        user = await auth(websocket)
        if user is None:
            return
        self.users[user.user_id].add(websocket)
        self.user_names[user.user_id] = user.name
        await self._emitter.emit('join', (user, websocket))
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
                self.users[user.user_id].remove(websocket)
                await self._emitter.emit('leave', user)
                raise
            self._debug(f'Received message {tag} from {user}: {trunc(data)}')
            await self._emitter.emit('message', (tag, data, user, websocket))

    async def serve_admin(self, websocket: WebSocketServerProtocol):
        self.admin.add(websocket)
        await self._emitter.emit('admin-join', websocket)
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
                self.admin.remove(websocket)
                await self._emitter.emit('admin-leave', None)
                raise
            await self._emitter.emit(
                'message',
                (f'admin-{tag}', data, None, websocket),
            )

    async def broadcast(self, data: str, with_admin: bool = True):
        _d = trunc(data)
        self._debug(f'Broadcasting message {_d}')
        all_users = (
            chain(self.users.items(), (('admin', self.admin),))
            if with_admin and self.admin is not None else self.users.items()
        )
        for uid, socks in all_users:
            user_name = 'admin' if uid == 'admin' else self.user_names[uid]
            self._debug(f'Broadcast to {user_name} message {_d}')
            socks_ = list(socks)
            for sock in socks_:
                try:
                    await sock.send(data)
                except ConnectionClosed:
                    pass

    async def _send_to_socks(
            self,
            dbg_info: str,
            socks: Iterable[WebSocketServerProtocol],
            data: str,
    ) -> Tuple[int, Dict[str, str]]:
        sent = {}
        n_sent = 0
        for _sock in socks:
            dbg_sock = self._wsfmt(_sock)
            try:
                await _sock.send(data)
                sent[dbg_sock] = 'OK'
                n_sent += 1
            except ConnectionClosed:
                self._debug(f'Writing on closed {dbg_info} sock {dbg_sock}')
                sent[dbg_sock] = 'NO'

        return n_sent, sent

    async def user_send(
            self,
            user_id: int,
            data: str,
            sock: Optional[WebSocketServerProtocol] = None,
    ) -> bool:
        user_name = self.user_names[user_id]
        if sock:
            socks = [sock]
            dbg_appendix = 'specific socket'
        else:
            socks = self.users[user_id]
            dbg_appendix = 'all sockets'
        n_sent, sent = await self._send_to_socks(user_name, socks, data)
        self._debug(
            f'Sent to {user_name} {dbg_appendix}: {sent} '
            f'message {trunc(data)}'
        )
        return bool(n_sent)

    async def admin_send(
            self,
            data: str,
            sock: Optional[WebSocketServerProtocol] = None,
    ) -> bool:
        if sock:
            socks = [sock]
            dbg_appendix = 'specific socket'
        else:
            socks = self.admin
            dbg_appendix = 'all sockets'
        n_sent, sent = await self._send_to_socks('admin', socks, data)
        self._debug(
            f'Sent to admin {dbg_appendix}: {sent} '
            f'message {trunc(data)}'
        )
        return bool(n_sent)

    async def kick(self, user_id: int):
        user = self.users[user_id]
        log.debug(f'Kicking user {user_id}')
        socks = list(user)
        for sock in socks:
            await sock.send(rerr('kick'))
            await sock.close(1000, 'kick')


rooms: Dict[str, GameRoom] = dict()

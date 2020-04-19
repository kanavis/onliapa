import asyncio
import logging
import random
import time
from collections import defaultdict
from typing import Set, Dict, Union, Optional, List, Tuple, Callable, Awaitable

from websockets import WebSocketServerProtocol

from game.helpers import state_serialize, state_deserialize
from server.auth import User
from server import messages as msg
from server.protocol import rmsg, rerr
from server.room import GameRoom, EventEmitter, EventHandler

log = logging.getLogger('onliapa.game')


class StateChangeFailed(Exception):
    pass


class Hat:
    def __init__(self):
        self._words: Set[str] = set()

    def put(self, word: str):
        self._words.add(word.lower())

    def remove(self, word: str):
        try:
            self._words.remove(word)
        except KeyError:
            pass

    def get(self) -> str:
        return random.choice(list(self._words))

    def serialize(self):
        return {
            'words': list(self._words),
        }

    def deserialize(self, state: dict):
        self._words = set(state['words'])

    def __len__(self):
        return len(self._words)


class Timer:
    def __init__(self, start: float, length: float):
        self.start = start
        self.length = length

    @property
    def time_left(self) -> float:
        return self.length - time.time() + self.start


class UserState:
    name = 'unknown'

    def to_message(self):
        raise NotImplementedError()

    def __str__(self):
        return self.name


class UserStateStandby(UserState):
    name = 'standby'

    def to_message(self):
        return {}


class UserStateAsking(UserState):
    name = 'asking'

    def __init__(self, timer: Timer, word: str, other: 'GameUser'):
        self.timer = timer
        self.word = word
        self.other = other

    def to_message(self):
        return {
            'state_asking': msg.UserStateAsking(
                time_left=int(self.timer.time_left),
                word=self.word,
                other=self.other.to_message(),
            ),
        }


class UserStateAnswering(UserState):
    name = 'answering'

    def __init__(self, timer: Timer, other: 'GameUser'):
        self.timer = timer
        self.other = other

    def to_message(self):
        return {
            'state_answering': msg.UserStateAnswering(
                time_left=int(self.timer.time_left),
                other=self.other.to_message(),
            ),
        }


class GameUser:
    user: User
    score: int
    state: Union[UserStateStandby, UserStateAsking, UserStateAnswering]
    guessed_words: List[str]

    def __init__(self, user):
        self.user = user
        self.state = UserStateStandby()
        self.score = 0
        self.guessed_words = []

    def add_point(self):
        self.score += 1

    def add_guessed_word(self, word: str):
        self.guessed_words.append(word)

    def __str__(self):
        return str(self.user)

    def serialize(self):
        return {
            'user': self.user.serialize(),
            'score': self.score,
            'guessed_words': self.guessed_words,
        }

    @classmethod
    def deserialize(cls, state: dict) -> 'GameUser':
        user = cls(user=User.deserialize(state['user']))
        user.score = state['score']
        user.guessed_words = state['guessed_words']
        return user

    def to_message(self) -> msg.User:
        return msg.User(
            user_name=self.user.name,
            user_id=self.user.user_id,
            score=self.score,
            guessed_words=self.guessed_words,
        )


class GameState:
    name = 'unknown'

    def to_message(self):
        raise NotImplementedError()

    def __str__(self):
        return self.name


class HatFillState(GameState):
    """ Filling the hat with words """
    name = 'hat_fill'
    words_per_user: Dict[int, int]
    users: Set[int]

    def __init__(self):
        self.words_per_user = defaultdict(lambda: 0)
        self.users = set()

    def to_message(self):
        return {'state_hat_fill': msg.StateHatFill(users=list(self.users))}


class GameStandbyState(GameState):
    """ Game is on standby """
    name = 'standby'

    def to_message(self):
        return {}


class RoundState(GameState):
    """ Pair is playing a round state """
    name = 'round'

    user_from: GameUser
    user_to: GameUser
    word: str
    timer: Timer
    guessed_words: List[str]

    def __init__(self, user_from: GameUser, user_to: GameUser, word: str,
                 timer: Timer):
        self.user_from = user_from
        self.user_to = user_to
        self.word = word
        self.timer = timer
        self.guessed_words = []

    def to_message(self):
        return {
            'state_round': msg.StateRound(
                asking=self.user_from.to_message(),
                answering=self.user_to.to_message(),
                time_left=int(self.timer.time_left),
                guessed_words=self.guessed_words,
            ),
        }


game_handler = EventHandler()
TState = Union[HatFillState, GameStandbyState, RoundState]


class Game:
    game_id: str
    game_name: str
    round_length: int
    hat_words_per_user: int

    room: GameRoom
    round_num: int
    hat: Hat
    users: Dict[int, GameUser]
    _state: TState

    def __init__(
        self,
        game_id: str,
        game_name: str,
        round_length: int,
        hat_words_per_user: int,
        state_saver: Callable[[str], Awaitable[None]],
    ):
        self.game_id = game_id
        self.game_name = game_name
        self.round_length = round_length
        self.hat_words_per_user = hat_words_per_user

        emitter = EventEmitter(game_handler, self)
        self.room = GameRoom(game_id, emitter)

        self.round_num = 0
        self.hat = Hat()
        self.users = dict()
        self._state = HatFillState()
        self._state_saver = state_saver

    @property
    def state(self) -> TState:
        return self._state

    async def _change_state(self, state: TState, reason=None, appendix=None):
        self._state = state
        await self._broadcast_game_state(reason=reason, appendix=None)

    def _info(self, message):
        log.info(f'Game {self.game_id}: {message}')

    def _warning(self, message):
        log.warning(f'Game {self.game_id}: {message}')

    async def _send_user_state(
        self,
        user: GameUser,
        sock: Optional[WebSocketServerProtocol] = None
    ):
        state_dict = dict(
            state_name=user.state.name,
            state_asking=None,
            state_answering=None,
        )
        state_dict.update(user.state.to_message())
        message = rmsg('user-state', msg.UserState(**state_dict))
        return await self.room.user_send(user.user.user_id, message, sock=sock)

    def to_message(self) -> msg.GameInfo:
        return msg.GameInfo(
            game_id=self.game_id,
            game_name=self.game_name,
            round_length=self.round_length,
            hat_words_per_user=self.hat_words_per_user,
            round_num=self.round_num,
            hat_words_left=len(self.hat),
        )

    def _game_state_msg(self, reason, appendix) -> str:
        state_dict = dict(
            state_name=self.state.name,
            users=list(u.to_message() for u in self.users.values()),
            reason=reason,
            appendix=appendix,
            state_hat_fill=None,
            state_round=None,
            game_info=self.to_message(),
        )
        state_dict.update(self.state.to_message())
        return rmsg('game-state', msg.GameState(**state_dict))

    async def _broadcast_game_state(self, reason=None, appendix=None):
        message = self._game_state_msg(reason=reason, appendix=appendix)
        await self.room.broadcast(message)

    async def _send_game_state(
            self,
            user: Optional[GameUser],
            reason=None,
            appendix=None,
            sock: Optional[WebSocketServerProtocol] = None
    ):
        message = self._game_state_msg(reason=reason, appendix=appendix)
        if user is None:
            await self.room.admin_send(message, sock=sock)
        else:
            await self.room.user_send(user.user.user_id, message, sock=sock)

    @game_handler.handler('join')
    async def event_join(self, data: Tuple[User, WebSocketServerProtocol]):
        user, sock = data
        if user.user_id not in self.users:
            # Create new game user
            game_user = GameUser(user)
            self.users[user.user_id] = game_user
            self._info(f'User {game_user} {user.user_id} joined')

            # Broadcast user joined game
            message = game_user.to_message()
            await self.room.broadcast(rmsg('new-user', message))
        else:
            game_user = self.users[user.user_id]
        # Send user and game state to user
        await self._send_user_state(game_user, sock=sock)
        await self._send_game_state(game_user, 'connect', sock=sock)

    @game_handler.handler('admin-join')
    async def event_admin_join(self, sock):
        await self._send_game_state(None, 'connect', sock=sock)

    @game_handler.message_handler('admin-kick-user', msg.UserId)
    async def event_kick_user(self, message: msg.UserId,
                              ws: WebSocketServerProtocol):
        user_id = message.user_id
        try:
            user = self.users[user_id]
            log.info(f'User {user.user.name} kicked by admin')
        except KeyError:
            await self.room.admin_send(rerr('no-such-user'), sock=ws)
            log.info(f'Wrong user {message.user_id} kick requested by admin')
            return
        del self.users[user_id]
        broadcast_msg = msg.UserId(user_id=user_id)
        await self.room.broadcast(rmsg('remove-user', broadcast_msg))
        await self.room.kick(user_id)

        if isinstance(self.state, HatFillState):
            if user_id in self.state.users:
                self.state.users.remove(user_id)
                await self._broadcast_game_state('remove-user')
        if (
            isinstance(self.state, RoundState) and
            (
                user_id == self.state.user_from.user.user_id or
                user_id == self.state.user_to.user.user_id
            )
        ):
            await self._stop_round(reason='kicked user')

    def _check_hat_full(self):
        return (
            isinstance(self.state, HatFillState) and
            self.state.users and
            not (set(self.users.keys()) - self.state.users)
        )

    @game_handler.message_handler('admin-hat-complete', msg.HatFillEnd)
    async def msg_admin_hat_complete(self, msg: msg.HatFillEnd,
                                     ws: WebSocketServerProtocol):
        if not isinstance(self.state, HatFillState):
            reply = rerr(
                'wrong-state',
                f'current state is {self.state}',
            )
            self._info(f'Admin hat end: wrong state {self.state}')
            await self.room.admin_send(reply, ws)
            return
        if msg.ignore_not_full:
            self._info('Admin requested hat fill completion, any hat state')
            if not self.state.users:
                self._info('Hat empty. Deny')
                await self.room.admin_send(
                    rerr('hat-empty', message='Hat empty'),
                    sock=ws,
                )
                return
        else:
            self._info('Admin requested hat fill completion')
            if not self._check_hat_full():
                self._info('Hat not full. Deny')
                await self.room.admin_send(
                    rerr('hat-not-full', message='Hat not full'),
                    sock=ws,
                )
                return

        if len(self.users) < 2:
            self._info(f'User count is {len(self.users)}. Deny hat fill end')
            await self.room.admin_send(
                rerr('users-not-enough', message='Not enough users'),
                sock=ws,
            )
            return

        self._info('Hat completed. Changing state')
        await self._change_state(GameStandbyState())
        await self._save_state()

    @game_handler.message_handler('hat-add-words', msg.HatAddWords)
    async def msg_hat_add_words(self, message: msg.HatAddWords, user: User,
                                ws: WebSocketServerProtocol):
        # Check state and data
        if not isinstance(self.state, HatFillState):
            reply = rerr(
                'wrong-state',
                f'current state is {self.state}',
            )
            self._info(f'User {user.name} put words: wrong state')
            await self.room.user_send(user.user_id, reply, ws)
            return
        l_words = len(message.words)
        if l_words != self.hat_words_per_user:
            reply = rerr(
                'wrong-data',
                f'wrong words length, {self.hat_words_per_user} exp',
            )
            self._info(f'User {user.name} put words: wrong num {l_words}')
            await self.room.user_send(user.user_id, reply, ws)
            return

        # Put words, update state
        for word in message.words:
            self.hat.put(word)
        self.state.users.add(user.user_id)
        self._info(f'User {user.name} put words to hat')

        # Broadcast
        await self._broadcast_game_state('user-put-words')

    @game_handler.message_handler('admin-start-round', msg.AdminStartRound)
    async def msg_admin_start_round(self, message: msg.AdminStartRound,
                                    ws: WebSocketServerProtocol):
        # Check state and data
        if not isinstance(self.state, GameStandbyState):
            reply = rerr(
                'wrong-state',
                f'current state is {self.state}',
            )
            self._info(f'Admin start round: wrong state')
            await self.room.admin_send(reply, ws)
            return
        if not len(self.hat):
            reply = rerr('hat-empty', 'hat is empty')
            self._info(f'Admin start round: hat empty')
            await self.room.admin_send(reply, ws)
            return

        try:
            user_from = self.users[message.user_id_from]
            user_to = self.users[message.user_id_to]
        except KeyError as err:
            reply = rerr(
                'wrong-data',
                f'wrong user provided: {err}',
            )
            self._info(f'Admin start round: wrong user id: {err}')
            await self.room.admin_send(reply, ws)
            return

        # Prepare word and objects
        word = self.hat.get()

        # Update state
        old_state = self.state
        round_num = self.round_num + 1
        round_timer = Timer(time.time(), float(self.round_length))
        await self._change_state(
            RoundState(user_from, user_to, word, round_timer),
            'round-start',
        )
        self._info(f'Admin starts round {round_num}: {user_from} -> {user_to}')

        try:
            # Update answering state
            user_to.state = UserStateAnswering(round_timer, user_from)
            res = await self._send_user_state(user_to)
            if not res:
                reply = rerr(
                    'unavailable-user',
                    user_to.user.name,
                )
                self._info(f'Answering user {user_from} is unavaiable')
                await self.room.admin_send(reply, ws)
                raise StateChangeFailed()

            # Update asking state
            user_from.state = UserStateAsking(round_timer, word, user_from)
            res = await self._send_user_state(user_from)
            if not res:
                reply = rerr(
                    'unavailable-user',
                    user_from.user.name,
                )
                self._info(f'Asking user {user_from} is unavaiable')
                await self.room.admin_send(reply, ws)
                raise StateChangeFailed()
        except Exception as err:
            self._warning(f'Aborting the round {round_num}, error: {err}')
            await self._change_state(old_state, 'round-cancel')
            if not isinstance(err, StateChangeFailed):
                raise
            return

        # Start task to update state in timeout
        self.round_num = round_num
        self.state.start_ts = time.time()
        await asyncio.create_task(self.await_stop_round())

    @game_handler.message_handler('word-guessed', msg.Empty)
    async def msg_word_guessed(self, message: msg.Empty, user: User,
                               ws: WebSocketServerProtocol):
        # Check state and data
        if not isinstance(self.state, RoundState):
            reply = rerr(
                'wrong-state',
                f'current state is {self.state}',
            )
            self._info(f'User {user} word guessed: wrong state')
            await self.room.user_send(user.user_id, reply, ws)
            return
        if user.user_id != self.state.user_from.user.user_id:
            reply = rerr(
                'wrong-data',
                f'this user is not asking',
            )
            self._info(f'User {user} word guessed: wrong user. '
                       f'Asking user is {self.state.user_from}')
            await self.room.user_send(user.user_id, reply, ws)
            return

        # Update user score
        self._info(f'User {user}: user {self.state.user_to} scored')
        self.state.user_to.score += 1
        self.state.user_to.add_guessed_word(self.state.word)

        # Remove word
        self.hat.remove(self.state.word)
        self.state.guessed_words.append(self.state.word)

        # Broadcast
        msg_user_to = self.state.user_to.to_message()
        await self._broadcast_game_state(
            'user-guessed',
            {
                'user': msg_user_to,
                'word': self.state.word,
            },
        )

        # Check if round didn't stop.
        if isinstance(self.state, RoundState):
            # Make word again
            if len(self.hat):
                self.state.word = self.hat.get()
                self.state.user_from.state.word = self.state.word
                await self._send_user_state(self.state.user_from)
            else:
                await self._stop_round('out-of-words')

    async def _stop_round(self, reason='timeout'):
        self._info(f'Finishing the round {self.round_num}, {reason}')
        old_state = self.state
        await self._change_state(GameStandbyState(), 'round-finished')
        old_state.user_from.state = UserStateStandby()
        old_state.user_to.state = UserStateStandby()
        await self._send_user_state(old_state.user_from)
        await self._send_user_state(old_state.user_to)
        await self._save_state()

    async def await_stop_round(self):
        await asyncio.sleep(self.round_length)
        assert isinstance(self.state, RoundState)
        await self._stop_round()

    def serialize(self):
        return {
            'game_id': self.game_id,
            'game_name': self.game_name,
            'round_length': self.round_length,
            'hat_words_per_user': self.hat_words_per_user,
            'round_num': self.round_num,
            'hat': self.hat.serialize(),
            'users': {k: v.serialize() for k, v in self.users.items()},
        }

    async def _save_state(self):
        self._info('Saving game state')
        raw_state = self.serialize()
        log.debug(f'Raw state to save {raw_state}')
        state = state_serialize(raw_state)
        await self._state_saver(state)

    @classmethod
    def load_state(cls, raw_state: str,
                   state_saver: Callable[[str], Awaitable[None]]):
        state = state_deserialize(raw_state)
        log.debug(f'Loading game state {state}')
        game = cls(
            game_id=state['game_id'],
            game_name=state['game_name'],
            round_length=state['round_length'],
            hat_words_per_user=state['hat_words_per_user'],
            state_saver=state_saver,
        )
        game.round_num = state['round_num']
        game.hat.deserialize(state['hat'])
        game.users = {
            int(k): GameUser.deserialize(v)
            for k, v in state['users'].items()
        }
        game.room.user_names = {k: v.user.name for k, v in game.users.items()}
        game._state = GameStandbyState()
        return game

import asyncio
import logging
import random
import time
from collections import defaultdict
from typing import Set, Dict, Union

from websockets import WebSocketServerProtocol

from game.helpers import state_serialize
from server.auth import User
from server import messages as msg
from server.messages import UserPutWords
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
        return random.choice(self._words)

    def serialize(self):
        return {
            'words': list(self._words),
        }


class Timer:
    def __init__(self, start: float, length: float):
        self.start = start
        self.length = length

    @property
    def time_left(self) -> float:
        return self.length - time.time() + self.start


class State:
    name = 'unknown'

    def to_message(self):
        raise NotImplementedError()

    def __str__(self):
        return self.name


class UserStateStandby(State):
    name = 'standby'

    def to_message(self):
        return msg.Empty()


class UserStateAsking(State):
    name = 'asking'

    def __init__(self, timer: Timer, word: str, other: 'GameUser'):
        self.timer = timer
        self.word = word
        self.other = other

    def to_message(self):
        return msg.UserStateAsking(
            time_left=int(self.timer.time_left),
            word=self.word,
            other=self.other.to_message(),
        )


class UserStateAnswering(State):
    name = 'answering'

    def __init__(self, timer: Timer, other: 'GameUser'):
        self.timer = timer
        self.other = other

    def to_message(self):
        return msg.UserStateAnswering(
            time_left=int(self.timer.time_left),
            other=self.other.to_message(),
        )


class GameUser:
    user: User
    score: int
    state: Union[UserStateStandby, UserStateAsking, UserStateAnswering]

    def __init__(self, user):
        self.user = user

        self.score = 0

    def add_point(self):
        self.score += 1

    def __str__(self):
        return str(self.user)

    def serialize(self):
        return {
            'user': self.user.serialize(),
            'score': self.score,
        }

    def to_message(self) -> msg.User:
        return msg.User(
            user_name=self.user.name,
            user_id=self.user.user_id,
            score=self.score,
        )


class HatFillState(State):
    """ Filling the hat with words """
    name = 'hand_fill'
    words_per_user: Dict[int, int]
    users: Set[int]

    def __init__(self):
        self.words_per_user = defaultdict(lambda: 0)
        self.users = set()

    def to_message(self):
        return msg.Empty()


class GameStandbyState(State):
    """ Game is on standby """
    name = 'standby'

    def to_message(self):
        return msg.Empty()


class RoundState(State):
    """ Pair is playing a round state """
    name = 'round'

    user_from: GameUser
    user_to: GameUser
    word: str
    timer: Timer

    def __init__(self, user_from: GameUser, user_to: GameUser, word: str,
                 timer: Timer):
        self.user_from = user_from
        self.user_to = user_to
        self.word = word
        self.timer = timer

    def to_message(self):
        return msg.Empty()


game_handler = EventHandler()


class Game:
    game_id: str
    game_name: str
    round_length: int
    hat_words_per_user: int

    room: GameRoom
    round_num: int
    hat: Hat
    users: Dict[int, GameUser]
    state: Union[HatFillState, GameStandbyState, RoundState]

    def __init__(
            self,
            game_id: str,
            game_name: str,
            round_length: int,
            hat_words_per_user: int
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
        self.state = HatFillState()

    def _info(self, message):
        log.info(f'Game {self.game_id}: {message}')

    def _warning(self, message):
        log.warning(f'Game {self.game_id}: {message}')

    async def _send_user_state(self, user: GameUser):
        state_name = user.state.name
        state_msg = user.state.to_message()
        message = rmsg('user-state', {'name': state_name, 'data': state_msg})
        return await self.room.user_send(user.user.user_id, message)

    async def _broadcast_game_state(self, reason=None, appendix=None):
        name = self.state.name
        data = self.state.to_message()
        message = rmsg(
            'game-state',
            {'name': name, 'reason': reason,
             'appendix': appendix, 'data': data}
        )
        await self.room.broadcast(message)

    @game_handler.handler('join')
    async def event_join(self, user: User):
        if user.user_id not in self.users:
            # Create new game user
            game_user = GameUser(user)
            self.users[user.user_id] = game_user
            self._info(f'User {game_user} joined')

            # Broadcast user joined game
            message = game_user.to_message()
            await self.room.broadcast(rmsg('new-user', message))

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
            await self.room.user_send_sock(user.user_id, ws, reply)
            return
        l_words = len(message.words)
        if l_words != self.hat_words_per_user:
            reply = rerr(
                'wrong-data',
                f'wrong words length, {self.hat_words_per_user} exp',
            )
            self._info(f'User {user.name} put words: wrong num {l_words}')
            await self.room.user_send_sock(user.user_id, ws, reply)
            return

        # Put words, update state
        for word in message.words:
            self.hat.put(word)
        self.state.users.add(user.user_id)
        self._info(f'User {user.name} put words to hat')

        # Broadcast
        b_message = UserPutWords(user_id=user.user_id)
        await self.room.broadcast(rmsg('user-put-words', b_message))

        # Check if hat is full
        if not (set(self.users.keys()) - self.state.users):
            self._info('Hat is full. Changing state.')
            self.state = GameStandbyState()
            await self.room.broadcast(rmsg('game-starts', {}))

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
            await self.room.admin_send_sock(ws, reply)
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
            await self.room.admin_send_sock(ws, reply)
            return

        # Prepare word and objects
        word = self.hat.get()

        # Update state
        old_state = self.state
        round_num = self.round_num + 1
        round_timer = Timer(time.time(), float(self.round_length))
        self.state = RoundState(user_from, user_to, word, round_timer)
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
                await self.room.admin_send_sock(ws, reply)
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
                await self.room.admin_send_sock(ws, reply)
                raise StateChangeFailed()

            # Send broadcast message
            await self._broadcast_game_state('round-start')
        except Exception as err:
            self._warning(f'Aborting the round {round_num}, error: {err}')
            self.state = old_state
            await self._broadcast_game_state()
            if not isinstance(err, StateChangeFailed):
                raise
            return

        # Start task to update state in timeout
        self.round_num = round_num
        self.state.start_ts = time.time()
        asyncio.create_task(self.await_stop_round())

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
            await self.room.user_send_sock(user.user_id, ws, reply)
            return
        if user.user_id != self.state.user_from.user.user_id:
            reply = rerr(
                'wrong-data',
                f'this user is not asking',
            )
            self._info(f'User {user} word guessed: wrong user. '
                       f'Asking user is {self.state.user_from}')
            await self.room.user_send_sock(user.user_id, ws, reply)
            return

        # Update user score
        self._info(f'User {user}: user {self.state.user_to} scored')
        self.state.user_to.score += 1

        # Update word
        self.hat.remove(self.state.word)
        self.state.word = self.hat.get()
        self.state.user_from.state.word = self.state.word
        await self._send_user_state(self.state.user_from)

        # Check if round didn't stop. If it did - send user state again
        if not isinstance(self.state, RoundState):
            await self._send_user_state(self.state.user_from)

        # Broadcast
        msg_user_to = self.state.user_to.to_message()
        await self._broadcast_game_state(
            'user-guessed',
            {
                'user': msg_user_to,
                'word': self.state.word,
            },
        )

    async def await_stop_round(self):
        await asyncio.sleep(self.round_length)
        assert isinstance(self.state, RoundState)
        self._info(f'Finishing the round {self.round_num}')
        old_state = self.state
        self.state = GameStandbyState()
        old_state.user_from.state = UserStateStandby()
        old_state.user_to.state = UserStateStandby()
        await self._broadcast_game_state('round-finished')
        await self._send_user_state(old_state.user_from)
        await self._send_user_state(old_state.user_to)
        await self._save_state()

    def serialize(self):
        return {
            'game_id': self.game_id,
            'round_length': self.round_length,
            'hat_words_per_user': self.hat_words_per_user,
            'round_num': self.round_num,
            'hat': self.hat.serialize(),
            'users': {k: v.serialize() for k, v in self.users.items()},
        }

    async def _save_state(self):
        state = state_serialize(self.serialize())
        message = rmsg('state-save', msg.StateSnapshot(state=state))
        await self.room.admin_send(message)

from typing import NamedTuple, List, Any, Optional
from marshmallow import Schema, fields, validate
from onliapa.server.protocol import message_type


@message_type
class AuthRequest(NamedTuple):
    class Schema(Schema):
        user_name = fields.String(
            required=True,
            validate=validate.Length(min=3)
        )

    user_name: str


@message_type
class UserId(NamedTuple):
    class Schema(Schema):
        user_id = fields.Integer()

    user_id: int


@message_type
class NewGameRequest(NamedTuple):
    class Schema(Schema):
        game_name = fields.String(
            required=True,
            validate=validate.Length(min=3, max=100),
        )
        round_length = fields.Integer(
            required=True,
            validate=validate.Range(min=10, max=1000),
        )
        hat_words_per_user = fields.Integer(
            required=True,
            validate=validate.Range(min=1, max=1000),
        )

    game_name: str
    round_length: int
    hat_words_per_user: int


@message_type
class HatAddWords(NamedTuple):
    class Schema(Schema):
        words = fields.List(
            cls_or_instance=fields.String(
                validate=validate.Length(min=2),
            ),
            validate=validate.Length(min=1),
        )

    words: List[str]


@message_type
class AuthUser(NamedTuple):
    user_name: str
    user_id: int


@message_type
class User(NamedTuple):
    user_name: str
    user_id: int
    score: int
    guessed_words: List[str]


@message_type
class AdminStartRound(NamedTuple):
    class Schema(Schema):
        user_id_from = fields.Integer(required=True)
        user_id_to = fields.Integer(required=True)

    user_id_from: int
    user_id_to: int


@message_type
class Empty(NamedTuple):
    class Schema(Schema):
        pass
    pass


@message_type
class GuessedWord(NamedTuple):
    word: str


@message_type
class GameInfo(NamedTuple):
    game_id: str
    game_name: str
    round_length: int
    hat_words_per_user: int
    round_num: int
    hat_words_left: int


@message_type
class UserStateAsking(NamedTuple):
    time_left: int
    word: str
    other: User


@message_type
class UserStateAnswering(NamedTuple):
    time_left: int
    other: User


@message_type
class StateHatFill(NamedTuple):
    users: List[int]


@message_type
class StateRound(NamedTuple):
    time_left: int
    asking: User
    answering: User
    guessed_words: List[str]


@message_type
class GameState(NamedTuple):
    game_info: GameInfo
    state_name: str
    state_hat_fill: Optional[StateHatFill]
    state_round: Optional[StateRound]
    users: List[User]
    reason: Optional[str]
    appendix: Any


@message_type
class UserState(NamedTuple):
    state_name: str
    state_asking: Optional[UserStateAsking]
    state_answering: Optional[UserStateAnswering]


@message_type
class HatFillEnd(NamedTuple):
    ignore_not_full: bool

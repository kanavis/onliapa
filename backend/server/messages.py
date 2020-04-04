from typing import NamedTuple, List
from marshmallow import Schema, fields, validate
from server.protocol import message_type


@message_type
class AuthRequest(NamedTuple):
    class Schema(Schema):
        user_name = fields.String(
            required=True,
            validate=validate.Length(min=3)
        )

    user_name: str


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
class User(NamedTuple):
    user_name: str
    user_id: int
    score: int


@message_type
class UserPutWords(NamedTuple):
    user_id: int


@message_type
class AdminStartRound(NamedTuple):
    class Schema(Schema):
        user_id_from = fields.Integer(required=True)
        user_id_to = fields.Integer(required=True)

    user_id_from: int
    user_id_to: int


@message_type
class StateSnapshot(NamedTuple):
    state: str


@message_type
class Empty(NamedTuple):
    class Schema(Schema):
        pass
    pass


@message_type
class GuessedWord(NamedTuple):
    word: str


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
class StateRound(NamedTuple):
    time_left: int
    asking: User
    answering: User
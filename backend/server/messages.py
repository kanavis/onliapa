from typing import NamedTuple
from marshmallow import Schema, fields, validate
from server.protocol import message_type


@message_type
class AuthRequest(NamedTuple):
    class Schema(Schema):
        username = fields.String(
            required=True,
            validate=validate.Length(min=3)
        )

    username: str

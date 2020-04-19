from typing import Any


class BaseError(Exception):
    pass


class CommunicationError(BaseError):
    pass


class ProtocolError(CommunicationError):
    pass


class RemoteError(CommunicationError):
    tag: str
    error: str
    data: Any

    def __init__(self, tag: str, error: str, data: Any):
        self.tag = tag
        self.error = error
        self.data = data

    def __str__(self):
        return 'RemoteError(tag={}, error="{}", data={}'.format(
            self.tag,
            self.error,
            self.data,
        )

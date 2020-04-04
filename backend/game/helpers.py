import json
import zlib
import base64


def state_serialize(state) -> str:
    return base64.b64encode(zlib.compress(json.dumps(state).encode())).decode()


def state_deserialize(state) -> str:
    return json.loads(zlib.decompress(base64.b64decode(state.encode())))

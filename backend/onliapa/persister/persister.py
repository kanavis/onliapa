""" Persister """
import aioredis


class PersisterError(Exception):
    pass


class GameDoesNotExist(PersisterError):
    pass


class CommunicationError(PersisterError):
    pass


class Persister:
    RECORD_TTL = 3600 * 24 * 60

    def __init__(self, redis_url: str):
        self.redis_url = redis_url

    async def _redis(self):
        return await aioredis.create_redis_pool(self.redis_url)

    async def ping(self):
        try:
            redis = await self._redis()
            await redis.ping()
        except aioredis.errors.RedisError as err:
            raise CommunicationError(f'{err.__class__}: {err}')

    async def load_game(self, key: str) -> str:
        redis = await self._redis()
        try:
            res = await redis.get(f'game/{key}', encoding='utf-8')
            if res:
                return res
            else:
                raise GameDoesNotExist()
        except aioredis.errors.RedisError as err:
            raise CommunicationError(err) from err

    async def save_game(self, key: str, state: str):
        try:
            redis = await self._redis()
            await redis.setex(f'game/{key}', self.RECORD_TTL, state)
        except aioredis.errors.RedisError as err:
            raise CommunicationError(err) from err

    async def del_game(self, key: str):
        try:
            redis = await self._redis()
            await redis.delete(f'game/{key}')
        except aioredis.errors.RedisError as err:
            raise CommunicationError(err) from err

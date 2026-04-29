import redis
from shared.config import get_settings

_settings = get_settings()

# decode_responses=True → bytes yerine string döner
redis_client = redis.Redis.from_url(
    _settings.redis_url,
    decode_responses=True,
)

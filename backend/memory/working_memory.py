from backend.memory.redis_client import get_redis


class WorkingMemory:
    def __init__(self):
        self.redis = get_redis()

    def set(
    self,
    agent_id: str,
    key: str,
    value: str,
    ttl: int | None = None
  ) -> None:
      redis_key = f"working:{agent_id}:{key}"

      if ttl is None:
          self.redis.set(redis_key, value)
      else:
          self.redis.set(redis_key, value, ex=ttl)


    def get(self, agent_id: str, key: str) -> str | None:
        redis_key = f"working:{agent_id}:{key}"
        return self.redis.get(redis_key)

    def delete(self, agent_id: str, key: str) -> None:
        redis_key = f"working:{agent_id}:{key}"
        self.redis.delete(redis_key)

    def clear_agent(self, agent_id: str) -> None:
      pattern = f"working:{agent_id}:*"

      keys = self.redis.keys(pattern)

      if keys:
          self.redis.delete(*keys)
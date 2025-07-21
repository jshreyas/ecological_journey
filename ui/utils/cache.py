import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

CACHE_TTL = int(os.getenv("CACHE_TTL", 604800))  # Cache TTL in seconds


class CacheBackend:
    def get(self, key: str):
        raise NotImplementedError

    def set(self, key: str, value, ex: int = None):
        raise NotImplementedError

    def delete(self, *keys):
        raise NotImplementedError


class RedisClientBackend(CacheBackend):
    def __init__(self):
        import redis

        self.client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True,
        )

    def get(self, key):
        val = self.client.get(key)
        if val:
            try:
                return json.loads(val)
            except Exception:
                return val
        return None

    def set(self, key, value, ex=None):
        self.client.set(key, json.dumps(value), ex=ex)

    def delete(self, *keys):
        for key in keys:
            self.client.delete(key)


# TODO: check if these Upstash APIs are successful
class UpstashRestBackend(CacheBackend):
    def __init__(self):
        self.url = os.getenv("UPSTASH_REDIS_REST_URL")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        if not (self.url and self.token):
            raise RuntimeError("Upstash REST credentials not set")

    def get(self, key):
        resp = requests.get(f"{self.url}/get/{key}", headers={"Authorization": f"Bearer {self.token}"})
        if resp.status_code == 200:
            val = resp.json().get("result")
            if val:
                try:
                    return json.loads(val)
                except Exception:
                    return val
        return None

    def set(self, key, value, ex=None):
        data = json.dumps(value)
        url = f"{self.url}/set/{key}"
        if ex:
            url += f"?EX={ex}"
        requests.post(url, headers={"Authorization": f"Bearer {self.token}"}, data=data)

    def delete(self, *keys):
        for key in keys:
            requests.post(
                f"{self.url}/del/{key}",
                headers={"Authorization": f"Bearer {self.token}"},
            )


def get_cache_backend() -> CacheBackend:
    if os.getenv("UPSTASH_REDIS_REST_URL") and os.getenv("UPSTASH_REDIS_REST_TOKEN"):
        return UpstashRestBackend()
    return RedisClientBackend()


cache_backend = get_cache_backend()


def cache_get(key: str):
    value = cache_backend.get(key)
    if value:
        print(f"cache hit for key: {key}")
        return value
    else:
        print(f"cache miss for key: {key}")
        return None


def cache_set(key: str, value, ex: int = None):
    print(f"cache write: {key} with value: {value}")
    ttl = ex if ex is not None else CACHE_TTL
    cache_backend.set(key, value, ex=ttl)


def cache_del(*keys):
    for key in keys:
        print(f"Deleted cache key: {key}")
    cache_backend.delete(*keys)

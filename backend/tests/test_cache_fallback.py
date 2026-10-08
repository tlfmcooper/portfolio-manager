import asyncio
import pytest
from app.core.redis_client import RedisClient


@pytest.mark.asyncio
async def test_redis_outage_preserves_ttl_cache_and_coalesces_loads():
    cache = RedisClient()
    calls = 0

    async def load():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return {"value": 100}

    values = await asyncio.gather(*(cache.get_or_load("portfolio:1:metrics:USD", load, 60) for _ in range(8)))
    assert calls == 1
    assert all(value == {"value": 100} for value in values)
    values[0]["value"] = 0
    assert await cache.get("portfolio:1:metrics:USD") == {"value": 100}
    assert await cache.get("portfolio:1:metrics:CAD") is None
    await cache.delete_prefix("portfolio:1:")
    assert await cache.get("portfolio:1:metrics:USD") is None
    assert cache._loads == {}


@pytest.mark.asyncio
async def test_fallback_expires_and_is_bounded(monkeypatch):
    now = [100]
    monkeypatch.setattr("app.core.redis_client.monotonic", lambda: now[0])
    cache = RedisClient()
    await cache.set("short", {"value": 1}, ttl=10)
    now[0] = 111
    assert await cache.get("short") is None
    for i in range(600):
        await cache.set(str(i), i, ttl=60)
    assert len(cache._memory) == 512


@pytest.mark.asyncio
async def test_mutation_during_load_does_not_cache_old_result():
    cache = RedisClient()
    started, finish = asyncio.Event(), asyncio.Event()

    async def load():
        started.set()
        await finish.wait()
        return {"old": True}

    task = asyncio.create_task(cache.get_or_load("portfolio:1:metrics", load, 60))
    await started.wait()
    await cache.delete_prefix("portfolio:1:")
    finish.set()
    await task
    assert await cache.get("portfolio:1:metrics") is None


@pytest.mark.asyncio
async def test_redis_recovery_replays_mutation_invalidations(monkeypatch):
    cache = RedisClient()
    await cache.delete_prefix('portfolio:1:')
    await cache.delete('stock:quote:AAA')
    class Remote:
        def __init__(self):
            self.values = {'portfolio:1:metrics:USD': '"old"', 'stock:quote:AAA': '"old"'}
        async def ping(self): pass
        async def delete(self, key): self.values.pop(key, None)
        async def get(self, key): return self.values.get(key)
        async def scan_iter(self, match, count):
            for key in list(self.values):
                if key.startswith(match[:-1]): yield key
    remote = Remote()
    async def from_url(*args, **kwargs): return remote
    monkeypatch.setattr('app.core.redis_client.redis.from_url', from_url)
    await cache.ensure_connected()
    assert cache.connected
    assert remote.values == {}
    assert cache._dirty_keys == set()
    assert cache._dirty_prefixes == set()


@pytest.mark.asyncio
async def test_remote_failure_does_not_repeat_timeouts_for_every_cache_read():
    cache = RedisClient()
    class FailedRemote:
        calls = 0
        async def get(self, key):
            self.calls += 1
            raise ConnectionError('offline')
    remote = FailedRemote()
    await cache.set('local', 123, ttl=60)
    cache.connected, cache.redis = True, remote
    assert await cache.get('local') == 123
    assert await cache.get('local') == 123
    assert remote.calls == 1  # Later reads use the fallback without another timeout.

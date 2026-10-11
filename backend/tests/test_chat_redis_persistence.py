"""Real Redis integration; runs only when an isolated server binary is available."""
import asyncio
import shutil
import subprocess

import pytest
from cryptography.fernet import Fernet
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.services.chat_secrets import ChatSecrets


@pytest.mark.asyncio
async def test_encrypted_secret_survives_redis_and_backend_restart(tmp_path):
    binary = shutil.which("redis-server")
    if not binary:
        pytest.skip("redis-server is required for the isolated persistence test")
    socket = str(tmp_path / "redis.sock")
    key = Fernet.generate_key().decode()
    command = [binary, "--port", "0", "--unixsocket", socket, "--unixsocketperm", "700",
               "--dir", str(tmp_path), "--appendonly", "yes", "--appendfsync", "always",
               "--maxmemory-policy", "noeviction", "--save", ""]

    async def start():
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        client = Redis(unix_socket_path=socket, socket_connect_timeout=1, decode_responses=True)
        for _ in range(100):
            try:
                await client.ping()
                return process, client
            except RedisError:
                await asyncio.sleep(0.02)
        process.terminate()
        process.wait(timeout=5)
        await client.aclose()
        pytest.fail("Isolated Redis failed to start")

    process, client = await start()
    try:
        secrets = ChatSecrets(client, key)
        await secrets.save(17, "persistence-test-secret")
        assert await client.ttl(secrets.storage_key(17)) == -1
        assert "persistence-test-secret" not in await client.get(secrets.storage_key(17))
        assert (await client.config_get("maxmemory-policy"))["maxmemory-policy"] == "noeviction"
        await client.aclose()
        # Simulate a crash; appendfsync always must preserve the acknowledged write.
        process.kill()
        process.wait(timeout=5)
        process, client = await start()
        restarted = ChatSecrets(client, key)
        assert await restarted.read(17) == "persistence-test-secret"
        assert await restarted.read(18) is None
        assert await client.ttl(restarted.storage_key(17)) == -1
        for path in tmp_path.rglob("*.aof"):
            assert b"persistence-test-secret" not in path.read_bytes()
    finally:
        await client.aclose()
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)

"""
Sync Redis data from local Redis to Upstash Redis.
Copies all keys and their values from source to destination.
"""

import asyncio
import redis.asyncio as redis
from app.core.config import settings


async def sync_redis():
    """Copy all data from local Redis to Upstash Redis."""
    print("🔄 Syncing Redis data from local to Upstash...")
    print("=" * 60)

    # Local Redis connection (port 6381 from podman-compose)
    local_redis_url = "redis://localhost:6381/0"
    print(f"📍 Source (Local): {local_redis_url}")

    # Upstash Redis connection
    upstash_redis_url = settings.REDIS_URL
    print(f"📍 Target (Upstash): {upstash_redis_url[:50]}...")

    try:
        # Connect to both Redis instances
        local_client = redis.from_url(local_redis_url, decode_responses=True)
        upstash_client = redis.from_url(upstash_redis_url, decode_responses=True)

        # Test connections
        await local_client.ping()
        await upstash_client.ping()
        print("✅ Connected to both Redis instances\n")

        # Get all keys from local Redis
        keys = await local_client.keys("*")

        if not keys:
            print("⚠️  No keys found in local Redis")
            return

        print(f"📊 Found {len(keys)} keys in local Redis\n")

        copied_count = 0
        failed_count = 0

        # Copy each key
        for key in keys:
            try:
                # Get key type
                key_type = await local_client.type(key)

                if key_type == "string":
                    # Copy string value
                    value = await local_client.get(key)
                    ttl = await local_client.ttl(key)

                    if ttl > 0:
                        await upstash_client.setex(key, ttl, value)
                    else:
                        await upstash_client.set(key, value)

                    print(f"✅ {key} (string, TTL: {ttl if ttl > 0 else 'none'})")
                    copied_count += 1

                elif key_type == "list":
                    # Copy list values
                    values = await local_client.lrange(key, 0, -1)
                    ttl = await local_client.ttl(key)

                    # Clear existing list and add all values
                    await upstash_client.delete(key)
                    if values:
                        await upstash_client.rpush(key, *values)

                    if ttl > 0:
                        await upstash_client.expire(key, ttl)

                    print(
                        f"✅ {key} (list, {len(values)} items, TTL: {ttl if ttl > 0 else 'none'})"
                    )
                    copied_count += 1

                elif key_type == "hash":
                    # Copy hash values
                    hash_data = await local_client.hgetall(key)
                    ttl = await local_client.ttl(key)

                    await upstash_client.delete(key)
                    if hash_data:
                        await upstash_client.hset(key, mapping=hash_data)

                    if ttl > 0:
                        await upstash_client.expire(key, ttl)

                    print(
                        f"✅ {key} (hash, {len(hash_data)} fields, TTL: {ttl if ttl > 0 else 'none'})"
                    )
                    copied_count += 1

                elif key_type == "set":
                    # Copy set values
                    members = await local_client.smembers(key)
                    ttl = await local_client.ttl(key)

                    await upstash_client.delete(key)
                    if members:
                        await upstash_client.sadd(key, *members)

                    if ttl > 0:
                        await upstash_client.expire(key, ttl)

                    print(
                        f"✅ {key} (set, {len(members)} members, TTL: {ttl if ttl > 0 else 'none'})"
                    )
                    copied_count += 1

                else:
                    print(f"⚠️  {key} (unsupported type: {key_type})")
                    failed_count += 1

            except Exception as e:
                print(f"❌ {key}: {str(e)}")
                failed_count += 1

        print("\n" + "=" * 60)
        print(f"✨ Sync complete!")
        print(f"   Copied: {copied_count}")
        print(f"   Failed: {failed_count}")
        print(f"   Total:  {len(keys)}")

        # Close connections
        await local_client.close()
        await upstash_client.close()

    except redis.ConnectionError as e:
        print(f"\n❌ Connection error: {e}")
        print("\n💡 Make sure:")
        print("   1. Local Redis is running: redis-server")
        print("   2. Upstash credentials are correct in .env")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(sync_redis())

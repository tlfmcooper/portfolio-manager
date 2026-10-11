# Chatbot API-key storage

The chatbot saves one Gemini API key per authenticated user, encrypted with Fernet
in Redis under `secrets:chat:gemini:{user_id}`. Keys have no expiration. The browser
sends a key only when saving/replacing it, clears the input after success, and
subsequently receives configuration status only. Gemini requests, including
screenshots and function-call follow-ups, go through the authenticated backend.
Existing `gemini_api_key` localStorage entries are deleted; users must re-enter
their keys once. Other browser settings and authentication storage are unchanged.

## Backend configuration

Set these in your backend environment or deployment Secret:

- `CHAT_SECRET_ENCRYPTION_KEY`: a persistent Fernet key. Generate it once using
  `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`.
  Keep it outside Redis and source control. All backend replicas must use the
  same value. Back it up separately: losing/changing it makes existing keys
  unreadable. Never generate a new value on each restart.
- `CHAT_SECRETS_REDIS_URL`: the durable secrets Redis connection URL. When unset,
  the backend uses `REDIS_URL`. Prefer a dedicated Redis instance so cache cleanup,
  eviction, and flush operations cannot remove secrets. Use `rediss://` when your
  Redis provider requires TLS and use its authenticated connection URL.
- `CHAT_GEMINI_MODEL`: server-selected model; defaults to `gemini-3.8-flash`, matching
  the previous widget default. Set this to a Gemini model available to your users.
  The previous frontend `VITE_GEMINI_MODEL` variable no longer controls chat.

Missing or invalid encryption configuration, Redis failures, and corrupt or
unreadable ciphertext fail explicitly. There is no in-memory or browser-storage
fallback. Saving reports success only after Redis acknowledges the encrypted write.
Users can replace or remove saved keys through chat settings.

## Durable Redis

`podman-compose.yml` includes an internal `chat-secrets` Redis service with a named
volume, AOF enabled, `appendfsync always`, and `maxmemory-policy noeviction`. Set
`CHAT_SECRET_ENCRYPTION_KEY` in `backend/.env` before starting the stack. Compose
sets the backend secrets URL to this service automatically and does not publish
its port. Back up the named volume as well as the encryption key; do not remove
that volume when recreating containers.

For the current k3s deployment, supply the backend environment values through
`../gitops-alikone` deployment configuration and provision durable Redis with a PVC
and the same AOF/eviction settings. This change does not deploy or alter the cluster.
Check managed Redis persistence and eviction settings explicitly; no TTL alone
does not protect a key from process restarts or eviction. Use backups to recover
from infrastructure loss or accidental deletion. Do not run cache flushes on the
secrets instance. Monitor Redis availability, disk/memory usage, persistence
health, and chat endpoint 503 responses without recording request bodies or keys.

The streaming endpoint returns `text/event-stream` with `Cache-Control: no-store`
and `X-Accel-Buffering: no`. Disable buffering for this endpoint in any additional
reverse proxy. Secret status/save/delete responses also use `no-store`.

## API

All routes require the existing active-user JWT authentication:

- `GET /api/v1/chat/api-key` returns `{ "configured": true | false }`.
- `PUT /api/v1/chat/api-key` accepts `{ "api_key": "..." }`, replaces any saved key,
  and returns configured status. Validation errors never echo the submitted key.
- `DELETE /api/v1/chat/api-key` removes the key and returns configured false.
- `POST /api/v1/chat/generate` accepts Gemini `contents`, `systemInstruction`, and
  `tools`. It uses only the authenticated user's saved key. Successful SSE events
  carry Gemini candidates; `{ "done": true }` ends a completed stream. A sanitized
  `{ "error": "..." }` event signals interruption after streaming starts.

## Verification

```sh
PYTHONPATH=backend pytest backend/tests/test_chat.py backend/tests/test_chat_redis_persistence.py -q
cd frontend
npm test -- --run tests/unit/chatClient.test.js tests/unit/PortfolioChatWidget.test.jsx tests/unit/chatAuth.test.jsx
npm run build
```

The persistence integration test requires `redis-server` on PATH; it runs its own
isolated Redis process with a temporary Unix socket and never touches configured
Redis or the application database.

# Local testing against the cluster database

The local backend uses the portfolio PostgreSQL database in the `portfolio` Kubernetes namespace through a loopback-only port-forward. Changes made in the local app update the same database used by the deployed app. Sign in with your usual portfolio credentials.

## Database tunnel

Keep this running in a terminal:

```sh
kubectl --context default -n portfolio port-forward --address 127.0.0.1 service/postgres-portfolio 15432:5432
```

The tunnel ends if its terminal closes or the selected database pod restarts. Restart it with the same command.

Database credentials have been saved in `backend/.env.local`, which is ignored by Git and has owner-only permissions. The URL points to `127.0.0.1:15432/portfolio_db`. Do not copy the credentials into tracked files.

## Backend

```sh
cd /Users/alikone/Projects/portfolio-manager/backend
PYTHONPATH=.. ../.venv/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Use this command without the earlier `DATABASE_URL=sqlite...` prefix: shell environment variables take precedence over the local config file. Restart the backend after editing the environment file.

Readiness: `http://127.0.0.1:8000/health` should report `database.type` as `postgresql` and `database.status` as `connected`. API documentation is available at `http://127.0.0.1:8000/docs`.

The backend reuses a bounded PostgreSQL connection pool so the tunnel does not require a new database authentication handshake for every request. Set `DATABASE_USE_NULL_POOL=true` only if your database environment requires connections to close after each request.

Redis points to the local machine. If Redis is not running, the app uses its in-process fallback cache; cluster Redis credentials are not required for this setup.

## Frontend

```sh
cd /Users/alikone/Projects/portfolio-manager/frontend
VITE_API_URL=http://127.0.0.1:8000/api/v1 npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open `http://127.0.0.1:5173`. Keep the tunnel and both servers running while testing. Ctrl+C stops a process.

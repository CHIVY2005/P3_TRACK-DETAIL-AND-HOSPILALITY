# System Boot Report

## Timestamp

- `2026-07-11 17:15:00 +07:00`

## Infrastructure Status

| Component | Status | Evidence |
|---|---:|---|
| PostgreSQL | Healthy | `guardian_postgres` is running on `0.0.0.0:5432->5432/tcp` and `netstat` shows port `5432` listening |
| Redis | Healthy | `guardian_redis` is running on `0.0.0.0:6379->6379/tcp` and `netstat` shows port `6379` listening |
| FastAPI Backend | Healthy | `GET http://127.0.0.1:8001/api/v1/health` returned `200` |
| React UI | Healthy | Vite is running on `http://127.0.0.1:3000/` and `netstat` shows port `3000` listening |

## Bugs & Port Conflicts Fixed

- Fixed Docker database incompatibility by updating `docker-compose.yml` from `postgres:15-alpine` to `postgres:16-alpine` so the existing data volume could boot without being dropped.
- Recreated `guardian_postgres` successfully after the version alignment.
- Restarted the backend in reload mode on port `8001` using the current workspace code.
- Started the frontend dev server on port `3000`.
- No npm dependency repair was needed because `node_modules` was already present.
- No manual PID kill was required in the final boot path because the services came up cleanly after the Docker recreate and restart.

## E2E Ready Confirmation

- Backend health endpoint is green.
- Frontend dev server is green.
- Docker Postgres and Redis are both reachable.
- The system is ready for multi-tab demo flow and AI Agent presentation.

### Notes

- Backend health currently reports the runtime database path used by the app configuration.
- The boot objective for infrastructure and demo readiness has been met without dropping the database volume.

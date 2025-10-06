# User Registration API (FastAPI · Postgres · Redis · Outbox)

A production-grade take-home that implements user registration and activation with a 4-digit code, plus a minimal login/session layer for demos.

- Create user → store pending user, enqueue an email with a 4-digit code
- Send code via an HTTP "SMTP" mock (treated as a third-party)
- Activate with Basic Auth + 4-digit code (valid for 60s, single-use)
- Login with Basic Auth → Bearer token (stored in Redis)
- `/me` with Bearer token

## TL;DR (Quickstart)

```bash
# 0) Build and boot everything
make up
make wait-db
make migrate

# 1) Open Swagger
open http://localhost:8000/docs

# 2) Create a user (POST /v1/users)
# 3) Get the 4-digit code (see "Get your code" below)
# 4) Activate (POST /v1/users/activate with Basic Auth)
# 5) Login (POST /v1/users/login with Basic Auth)
# 6) Call /v1/users/me with the returned Bearer token
```

## Prerequisites

- Docker & Docker Compose
- No local Python/node needed — everything runs in containers

## Run the stack

```bash
# Build & start services (api, db, redis, smtp-mock)
make up
make wait-db

# Run DB migrations
make migrate

# Follow API logs (handy during the demo)
make logs s=api

# Follow the mock smtp server to retrieve code
make logs s=smtp-mock
```

### Services

- **API**: http://localhost:8000 (Swagger: /docs)
- **Postgres**: app@app@db:5432/app
- **Redis**: redis:6379/0
- **SMTP mock**: HTTP server that accepts POST /send and logs messages

## Endpoints (overview)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/v1/users/` | — | Register user (pending) & send 4-digit code |
| POST | `/v1/users/activate` | Basic | Activate with code (valid 60s, single-use) |
| POST | `/v1/users/login` | Basic | Login → returns Bearer token (Redis) |
| GET | `/v1/users/me` | Bearer | Get current user profile |



## Demo flow (Swagger)

Open Swagger at http://localhost:8000/docs.

### Register

Expand POST `/v1/users/` → Try it out → send JSON:

```json
{ "email": "me@example.com", "password": "s3cret" }
```

You should get 202 Accepted.

### Get your code (two options)

#### A. From DB outbox (robust)

```bash
EMAIL="me@example.com"
docker compose exec -T db psql -U app -d app -tA \
  -c "select payload->>'body' from outbox
      where topic='user.verification_code' and payload->>'to'='${EMAIL}'
      order by created_at desc limit 1;" \
  | grep -Eo '[0-9]{4}' | tail -1
```

#### B. From SMTP mock logs (quick)

```bash
docker logs beefirst_technical_test-smtp-mock-1 --since 2m 2>&1 \
  | grep -Eo 'Your code is [0-9]{4}' | tail -1
# look for: "Your code is 1234"
```

### Activate

In Swagger, expand POST `/v1/users/activate` → Try it out.
Click the Authorize button at the top-right, choose HTTP basic,
enter email / password from step 2, then in the request body provide:

```json
{ "code": "1234" }
```

You should see 200 OK.

### Login

Still using HTTP basic in Swagger (same credentials), expand
POST `/v1/users/login` → Execute. Copy the token from the response.

### /me (Bearer)

Click Authorize again, but choose the Bearer/JWT scheme this time.
Paste the token into the Bearer field (no Bearer prefix; Swagger adds it).
Now open GET `/v1/users/me` → Execute → you should get your profile.

> If Swagger says "missing bearer token," you likely pasted the token into the Basic auth dialog. Use the Bearer scheme for `/me`.

## Demo flow (cURL)

```bash
EMAIL="me+$RANDOM@example.com"
PASS="s3cret"

# Register
curl -s -X POST http://localhost:8000/v1/users/ \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}"

# Grab the latest code from the outbox (DB)
CODE=$(docker compose exec -T db psql -U app -d app -tA \
  -c "select payload->>'body' from outbox
      where topic='user.verification_code' and payload->>'to'='${EMAIL}'
      order by created_at desc limit 1;" \
  | grep -Eo '[0-9]{4}' | tail -1)

# Activate (Basic Auth)
curl -i -u "$EMAIL:$PASS" \
  -H 'Content-Type: application/json' \
  -d "{\"code\":\"$CODE\"}" \
  http://localhost:8000/v1/users/activate

# Login (Basic Auth) → token
TOKEN=$(curl -s -u "$EMAIL:$PASS" -X POST http://localhost:8000/v1/users/login | jq -r .token)

# /me (Bearer)
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/v1/users/me | jq
```

## Makefile targets

| Command | Description |
|---------|-------------|
| `make up` | docker compose up -d |
| `make down` | stop & remove volumes |
| `make wait-db` | wait until Postgres is ready |
| `make migrate` | run DB migrations |
| `make migration name="my_feature"` | scaffold a new migration |
| `make logs s=api` | follow container logs (api/db/redis/smtp-mock) |
| `make test` | run tests inside the container (no bind mounts) |
| `make test-coverage` | same, with coverage |
| `make test-all` | up + build + wait-db + migrate + test |
| `make test-ci` | single entry for CI (same as test-all) |

## Tests & Coverage

```bash
# full test suite (unit + integration)
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm -T api \
  pytest -q --cov=app --cov-report=term-missing
```

**Notes:**
- Integration tests spin up real Postgres/Redis in Compose
- The mock SMTP is an HTTP service; we exercise it via outbox dispatcher tests

## Configuration

All config is centralized in `app/settings.py` (Pydantic settings). Override via env vars:

| Env var | Default | Meaning |
|---------|---------|---------|
| `DATABASE_URL` | `postgresql://app:app@db:5432/app` | Postgres DSN |
| `REDIS_URL` | `redis://redis:6379/0` | Redis URL |
| `SMTP_BASE_URL` | `http://smtp-mock:8025` | Third-party "SMTP" HTTP endpoint |
| `CODE_TTL_SECONDS` | `60` | Activation code validity (seconds) |
| `RESEND_THROTTLE_SECONDS` | `60` | Cooldown between resend attempts |
| `CODE_ATTEMPTS` | `5` | Max attempts per code (policy placeholder) |
| `SESSION_TTL_SECONDS` | `86400` (24h) | Login session TTL in Redis |
## Architecture (high level)

```
        ┌─────────────┐           ┌────────┐
        │   FastAPI   │──────────▶│  /docs │
        │  (Routers)  │           └────────┘
        │             │
        │  Use-cases  │  register / activate / login / me
        │ (App layer) │
        ├─────────────┤
        │   Domain    │  Entities (User), Policies, Services
        ├─────────────┤
        │  Infra      │
        │  Postgres   │  Repos (no ORM), UnitOfWork, Outbox table
        │  Redis      │  Activation codes (salt+digest; Lua CAS delete),
        │             │  Sessions (Bearer tokens with TTL)
        │  HTTP       │  SMTP adapter (third-party via httpx)
        └─────────────┘
```

### Flow

1. `POST /v1/users` → create/update pending user, generate 4-digit code, store (salt, digest) in Redis with TTL, enqueue email in Postgres outbox
2. Worker/dispatcher (or test harness) sends email to SMTP mock (HTTP)
3. `POST /v1/users/activate` (Basic Auth) + code → verify via Redis (single-use), mark user active in Postgres
4. `POST /v1/users/login` (Basic Auth) → create opaque session token in Redis
5. `GET /v1/users/me` (Bearer token) → load session → fetch user → return profile


## Key choices

- **No ORM**: Repositories are plain SQL with psycopg + psycopg_pool
- **Outbox pattern**: Email sending decoupled from HTTP request; robust to SMTP failures
- **Third-party SMTP**: Treated as HTTP service; idempotency header supported
- **Secure code storage**: Redis stores salt and digest (SHA-256 over salt||code); verify via Lua script to compare-and-delete (single use)
- **Sessions**: Opaque token stored in Redis with TTL → simple demo-friendly Bearer auth

## Troubleshooting

### "missing bearer token" in Swagger
Use the Bearer auth scheme (not Basic) for `/v1/users/me`. Click Authorize and select the Bearer scheme, then paste the token returned by `/login`.

### "invalid activation code"
The code is single-use and expires after `CODE_TTL_SECONDS` (default 60s). Regenerate by re-registering or (if exposed) using a resend endpoint.

### "user already active"
Activation is idempotent—once active, attempting activation again returns a user-state error.

### Want to see the email body?

- **From DB outbox (payload)**: see the cURL snippet above
- **From SMTP mock logs**: `docker logs beefirst_technical_test-smtp-mock-1 --since 2m`

### Start fresh

```bash
make down && make up && make wait-db && make migrate
```

## Notes

You can add a simple outbox worker container if you want real-time dispatch outside tests, e.g.:

```bash
docker compose run --rm -T api python -m app.infrastructure.outbox.worker_main
```

(The test suite already exercises the dispatcher thoroughly.)

Password hashing uses bcrypt (via passlib) in the infra layer.

## License

MIT
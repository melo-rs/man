# Man backend

Python 3.14, FastAPI, SQLAlchemy, PostgreSQL, and Alembic.

## Deploy to Vercel

Vercel uses `man.app:app` as one Python Function. From this directory, link a
Vercel project (or create one at the prompt):

```sh
vercel link
```

To add a new PostgreSQL database, run `vercel integration add neon` and select
the linked project and Production environment at the prompts. You can also
create or connect Neon in the project's **Storage** tab. The integration adds a
pooled `DATABASE_URL` to the selected environments; the app uses it directly.
If `DATABASE_URL_UNPOOLED` is available, Alembic uses that direct connection.
The existing `MAN_POSTGRES_*` settings remain a fallback when `DATABASE_URL`
is absent. For Preview deployments, connect a separate Neon branch so preview
requests do not write to the production database.

Connect a Vercel Blob store to that same project in its **Storage** tab. Enable
the Production environment when connecting it. Vercel then supplies
`BLOB_READ_WRITE_TOKEN` automatically. The backend also accepts the existing
`MAN_VERCEL_BLOB_READ_WRITE_TOKEN` setting for local use. The upload endpoint
returns a short-lived signed URL so the file goes directly to Blob. It accepts
PNG, JPEG, WebP, and AVIF images.
If you need a new store, `vercel blob create-store man-files` creates one and
prompts you to connect it to the linked project.

Set these Production variables in the project settings or with `vercel env add
NAME production` (which prompts for the value):

```text
MAN_ENV=production
MAN_PASSWORD=<strong password>
MAN_CORS_ORIGINS=["https://your-frontend.example"]  # optional: allow all request headers from this origin
```

CORS allows credentialed requests from any origin and reflects that origin in
the response. Origins listed in `MAN_CORS_ORIGINS` may also send any request
header; other origins may send `Authorization` and standard CORS headers.

Check that `vercel env ls production` includes `DATABASE_URL` from Neon and
`BLOB_READ_WRITE_TOKEN` from Blob. If using another PostgreSQL provider, set
`MAN_POSTGRES_HOST`, `MAN_POSTGRES_PORT`, `MAN_POSTGRES_DATABASE`,
`MAN_POSTGRES_USER`, and `MAN_POSTGRES_PWD` instead; its host must be reachable
from Vercel. Apply migrations from this checkout, then deploy and check the
health endpoint:

```sh
vercel env run -e production -- uv run alembic upgrade head
vercel deploy --prod
curl https://<deployment-url>/healthz
```

The deployment URL is printed by the CLI. `/healthz` also checks the database.
For a preview deployment, configure the same required variables and Blob store
for Preview and run `vercel deploy` without `--prod`. The `.vercelignore` file
keeps local `.env` files and test artifacts out of CLI uploads.

## Run the tests

For first-time setup, copy `.env.template` to `.env`, set `MAN_PASSWORD`, and
customize the other values as needed.
Install the locked development dependencies and start the shared PostgreSQL service:

```sh
uv sync --dev --locked
docker compose up -d --wait postgres
uv run task test
```

Development and tests use the same PostgreSQL 18.6 server on port `5432`.
Development uses the `man` database; tests create separate worker databases
such as `man_test_master` and `man_test_gw0`. Public test defaults live in the
tracked `.env.test`; tests select `MAN_ENV=test` before importing the app.
Environment variables override those defaults. If the server uses custom
credentials, host, or port, use matching values when running tests.

Useful commands:

```sh
# Run unit tests without starting a database
uv run task test_unit

# Parallel execution without coverage
uv run task test_fast

# Limit parallelism on larger machines
uv run task test_fast -n 2

# Run a file or a single case
uv run task test tests/products/test_endpoints.py
uv run task test tests/products/test_endpoints.py::test_missing_product

# Match CI's reports
uv run task test --cov-report=xml --cov-report=html --junitxml=test-results.xml

# Stop the shared service; its persistent volume retains development data
docker compose down
```

The PostgreSQL user must have permission to create and drop databases. The
Compose service's default `man` user has these permissions. Keep a separate test
database prefix in `MAN_POSTGRES_DATABASE`, such as `man_test`.

## Test conventions

Tests mirror application domains. Each domain uses `test_schemas.py`,
`test_repository.py`, and `test_endpoints.py` as needed. Mark database-backed
tests with `pytest.mark.integration` and async tests with `pytest.mark.anyio`.
AnyIO uses asyncio, matching asyncpg. Database initialization is session-scoped
and runs for tests that request a database fixture.

Shared fixtures live in `tests/fixtures`:

- `database`: one freshly migrated database per xdist worker, plus
  function-scoped transactions, sessions, and `save_fixture`.
- `base`: FastAPI dependency overrides and HTTPX clients that clear the test
  session's identity map before each request.
- `random_models`: typed async builders such as `create_product`, with explicit
  overrides and predictable defaults; names follow Polar's fixture conventions.

Repository tests use the real PostgreSQL database. `save_fixture` adds and
flushes models. Endpoint tests reuse the test session through a dependency
override. The HTTPX client expunges loaded objects before each request to catch
behavior that would otherwise depend on the session's identity map. Each test
starts an outer database transaction and rolls it back afterward.
The request-session lifecycle tests use a dedicated client with the real database
dependency and request savepoints to verify production commits and rollbacks.

Worker databases use the configured test prefix and worker ID: `master` for a
serial run and `gw0`, `gw1`, etc. for parallel runs. The initialization fixture
drops an existing worker database, recreates it, and applies migrations before
the suite. It drops the worker database again on normal teardown. Overlapping
test runs need different `MAN_POSTGRES_DATABASE` values because worker names are
reused. The configured base database and development database are left intact.

Routine HTTPX tests inject request state rather than starting application
lifespan.

## Authentication

Set `MAN_PASSWORD` in the environment or `.env` before starting the app. There
is one shared password and no registration endpoint. `POST /v1/login` accepts
`{"password": "..."}` and sets an HTTP-only session cookie. The session is stored
in PostgreSQL and expires 30 days after login; requests do not extend it.

```sh
curl -c cookies.txt -H 'Content-Type: application/json' \
  -d '{"password":"YOUR_PASSWORD"}' http://127.0.0.1:8000/v1/login
curl -b cookies.txt http://127.0.0.1:8000/v1/products
```

Product and offer GET endpoints are public so the storefront can load its
catalogue. Creating products or offers, and using `/v1/files`, still requires
the cookie. Prices are integer BRL centavos. Product records also include
`category`, `unit`, `gallery_urls`, and `options` for the storefront. Apply the
database migration before using these fields. Product image fields use absolute
HTTPS URLs, and offer responses include the associated product's `thumb_url`.

Authenticated `PUT` and `DELETE` endpoints at `/v1/products/{id}` and
`/v1/offers/{id}` support full edits and deletion in the administration panel.
Updating an offer also accepts `is_active`. Deleting a product cascades to its
offers. Product create and update requests may include `option_prices`, a map
from option name to price in BRL cents. The separate public
`GET /v1/product-option-prices` route returns these maps keyed by product ID.
Existing product and offer response JSON fields remain unchanged. Apply the
`0005` migration before using the new product field.

To import the storefront's initial 13 products and seven offers, run:

```sh
uv run alembic upgrade head
PYTHONPATH=. uv run python scripts/migrate_storefront_images.py
PYTHONPATH=. uv run python scripts/seed_storefront.py
```

The seed script leaves existing products and active offers alone. New offers
start when the script runs and expire seven days later. The image migration
requires the sibling `Emporio_GE` checkout, Vercel CLI, and a public Blob store
read-write token. It writes URLs to the local, ignored
`scripts/data/blob_urls.json`, so each environment can use its own store. The
script reuses existing blobs and leaves product records with custom images
untouched.

## Migrations and checks

Schemas are built from migrations, never `metadata.create_all()`. The model
registry must import new models so Alembic can discover them. Migrate and check
the development database with:

```sh
uv run task db_migrate
uv run alembic check
uv run task lint
uv run task type_check
```

CI starts a PostgreSQL service with a `man_test` database, migrates it, and runs
`alembic check`. It sets `MAN_TEST_DATABASE_TEMPLATE=man_test`, so worker
databases are cloned from that migrated template instead of applying migrations
again. Locally, the fixture applies migrations unless
`MAN_TEST_DATABASE_TEMPLATE` names an existing migrated template. Template
cloning retries briefly when another connection is using the template, matching
Polar's fixture.

CI uploads JUnit and XML/HTML coverage reports. Coverage is reported without a
minimum threshold. Optional xdist parallelism is available locally.

The database lifecycle and shared PostgreSQL setup follow
[Polar's backend fixtures at commit a4bae2b7](https://github.com/polarsource/polar/tree/a4bae2b742befdb6dcc696a841f259aed24f2086/server/tests/fixtures).

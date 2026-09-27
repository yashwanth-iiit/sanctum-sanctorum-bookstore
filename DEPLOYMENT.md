# Running and publishing the application

The API and supplied frontend run together as one Python service. No additional
application dependencies are required. The container uses the existing lockfile
and SQLite stored at `/data/sanctum.db`.

Public application: https://yashwanthbk.alwaysdata.net/
Public repository: https://github.com/yashwanth-iiit/sanctum-sanctorum-bookstore

The application is deployed on Alwaysdata's Free personal plan with persistent
SQLite storage. Public endpoints and data retention after a service restart
were verified on 27 September 2026.

## Local development and verification

From the folder containing `pyproject.toml`:

```bash
uv sync --frozen
uv run pytest
uv run pytest tests verification
uv run uvicorn app.main:app --reload
```

Open `http://localhost:8000/` for the app or `/docs` for the API explorer. A new
database seeds 12 books and four members: ID 1 supreme, ID 2 master, ID 3 adept,
ID 4 apprentice. These IDs are verified for a fresh database; confirm the actual
records when using an existing database. The UI selects a member by ID; it does
not implement production authentication or charge a real payment method.

## Container deployment

These commands use Podman. With Docker, replace `podman` with `docker` and omit
`--format docker` from the build command. That Podman option preserves the image's
health check, which its default OCI format otherwise omits.

```bash
podman build --format docker -t localhost/sanctum:local .
podman volume create sanctum-data
podman run --detach --name sanctum --publish 127.0.0.1:8000:8000 \
  --volume sanctum-data:/data localhost/sanctum:local
```

Use a named persistent volume, or a host/platform persistent disk mounted at
`/data` and writable by UID 10001. Data written only inside a replaceable
container filesystem will not survive replacement. Keep one instance/worker
for this SQLite demo. Back up the database using a SQLite-consistent backup
procedure, and keep backups outside the application instance.

Configuration:

| Setting | Default | Purpose |
|---|---|---|
| `PORT` | `8000` | Application listening port; configure the host's routing to match |
| `SANCTUM_DATABASE_URL` | `sqlite:////data/sanctum.db` in the image | Database location; the parent directory must exist and be writable |
| Public health check | `/health` | Basic application availability check |

The default outside the image remains `sqlite:///./sanctum.db`. If a host builds
directly from Python source instead of the Dockerfile, install with
`uv sync --frozen --no-dev`, configure a persistent database path, and start with
`uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port "$PORT"`.

The container recipe follows the official [uv Docker integration
guide](https://docs.astral.sh/uv/guides/integration/docker/) and pins the uv tool
version used for local verification. Application packages remain frozen by
`uv.lock`; base-image patch contents can vary over time, so pin an image digest
if a fully repeatable container base is needed.

## Publishing to GitHub

Create an empty **public** repository in your GitHub account. Leave automatic
README/gitignore/license initialization off because this local repository
already has history. Then use its actual URL:

```bash
git remote add origin <your-public-repository-url>
git push -u origin main
```

Do not squash the commits. The first commit preserves the exact ZIP starter;
upstream history was absent from the supplied archive. Confirm the repository
is viewable while logged out and record its URL in `NOTES.md`.

## Publishing to a hosting service

1. Choose a Python/container host that provides durable writable storage. Check
   its current storage, pricing, sleep behavior, and persistence guarantees
   before committing to it; a free compute tier may not include a persistent disk.
2. Connect the public GitHub repository and build from this Dockerfile, or use
   the source-build commands above.
3. Mount durable storage at `/data`, grant the runtime user write access, and
   configure `SANCTUM_DATABASE_URL` and `PORT` for that environment.
4. Expose the app through the host's public HTTPS URL and use `/health` for its
   availability check. Avoid horizontal scaling for the current SQLite design.
5. Open `/`, `/docs`, and all five UI panels. Create a member, purchase/pay a book,
   cancel a separate order, borrow/return a book, and inspect statistics/reports.
6. Restart/redeploy the service and verify that the member and operations persist
   and that seeding does not duplicate data.
7. Verify the URL in a fresh browser session, then replace the pending live URL
   in `NOTES.md` and record the actual provider/storage choices.

Hosted PostgreSQL is an alternative, but the project has no PostgreSQL DBAPI
driver and the assignment prohibits new dependencies. Resolve that exception
with the assignment author before switching. Merely changing the URL is
insufficient: the starter's SQLite-specific connection options would also need
to become conditional. No PostgreSQL support is claimed by this implementation.

## Alwaysdata free hosting

The free personal plan provides persistent disk storage, and its User program
site type supports FastAPI through Uvicorn. Confirm the account's actual free
plan before creating the site. No paid resources are needed for this demo.

In the hosting account's terminal, clone the public repository and install the
existing locked dependencies using uv:

```bash
git clone https://github.com/yashwanth-iiit/sanctum-sanctorum-bookstore.git
cd sanctum-sanctorum-bookstore
UV_CONCURRENT_DOWNLOADS=1 UV_CONCURRENT_INSTALLS=1 UV_CONCURRENT_BUILDS=1 \
  uv sync --frozen --no-dev --no-cache --python python3.12
```

Create a **User program** site with its account-provided public address and this
command, replacing ACCOUNT with the actual hosting account name:

```bash
sh /home/ACCOUNT/sanctum-sanctorum-bookstore/deploy/alwaysdata-start.sh
```

The provider supplies IP and PORT. The script keeps the SQLite database in
`$HOME/sanctum-data`, outside the source checkout. Use one process. After updates,
pull the repository and restart the site; verify existing records persist.

The deployed account is `yashwanthbk`, its source checkout is
`/home/yashwanthbk/sanctum-sanctorum-bookstore`, and its SQLite file is
`/home/yashwanthbk/sanctum-data/sanctum.db`. The successful installation used uv
0.10.10 with reduced concurrency on the resource-limited free plan. This is a
deployment tool, not an added application dependency.

References: [free plan](https://www.alwaysdata.com/en/offers/) and
[ASGI configuration](https://help.alwaysdata.com/en/docs/web-hosting/languages/python/configuration/).

## Existing databases

`create_all` creates missing tables; it does not migrate an older loan table to
the completed schema. For an existing database created from the starter, take a
backup and explicitly migrate it before using this version. For a disposable
demo, deliberately choose a new empty database path. Startup does not erase or
silently reset an existing database.

## Submission checks

- Local acceptance and additional verification tests pass.
- Deployment is publicly reachable and retains data across service replacement.
- Repository is public, its commits are intact, and no database/secret files are tracked.
- `NOTES.md` includes the real live URL, repository URL, usage instructions,
  decisions, limitations, test results, and honest AI disclosure.

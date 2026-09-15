# Business Management Backend

Django REST API with PostgreSQL for company administration, projects, reporting,
workflows, documents, and support.

## Local setup

Run commands from the repository root. Use Python 3.12 or newer (the Docker image
uses Python 3.13). Create and activate a virtual environment, then install the
development dependencies with `python -m pip install -r requirements-dev.txt`.
Docker is optional for local development.

Start PostgreSQL and create a database and database user. Configure `.env` in the
repository root with `SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`,
and `DB_PORT`. Use a strong secret key and keep `.env` private. For local HTTP
development, set `DEBUG=True`; otherwise HTTPS redirects are enabled.

With `DEBUG=True`, email defaults to the console backend: verification messages
appear in the server terminal instead of being delivered. Configure SMTP when
actual delivery is needed. Tests capture mail locally without sending it.
If connecting a frontend, set `FRONTEND_URL` and `CORS_ALLOWED_ORIGINS` to its origin.

Before upgrading an existing database, read the migration notes in
[the deployment runbook](deployment/RUNBOOK.md). For a new database, run
`python manage.py migrate`, then `python manage.py runserver`.
API routes use `/api/v1/`; internal administration is at `/internal/admin/`.
Create a platform administrator with `python manage.py createsuperuser` if needed.
API documentation is exposed at `/api/v1/docs/` only when `DEBUG=True`.

## Verification

```text
python manage.py check
python manage.py makemigrations --check --dry-run
python -m pytest -q
```

Tests require PostgreSQL and permission to create a separate test database and a
temporary schema within it. They do not apply migrations to the application database. Run
test processes sequentially unless each has a distinct test database name.

Production setup, the database upgrade procedure, and the OTP login contract are
documented in [deployment/RUNBOOK.md](deployment/RUNBOOK.md).

API schema generation currently reports incomplete annotations and other
diagnostics; passing the tests alone does not establish deployment readiness.

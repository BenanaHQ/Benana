.PHONY: poetry-install dev run fmt lint test migrate

poetry-install:
	poetry install --no-root

dev:
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run:
	poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

fmt:
	poetry run black app
	poetry run isort app

lint:
	poetry run mypy app || true

test:
	echo "no tests yet"

migrate:
	poetry run python -c "from app.core.migrator import bootstrap; bootstrap()"

# Alembic helpers (host migrations)
.PHONY: alembic-rev alembic-up alembic-down alembic-stamp

alembic-rev:
	cd server && poetry run alembic -c alembic.ini revision -m "$$msg"

alembic-up:
	cd server && poetry run alembic -c alembic.ini upgrade head

alembic-down:
	cd server && poetry run alembic -c alembic.ini downgrade -1

alembic-stamp:
	cd server && poetry run alembic -c alembic.ini stamp head

# Generate OpenAPI schema including dynamically loaded plugin routes
.PHONY: openapi
openapi:
	cd server && BENANA_OPENAPI_OUT=server/openapi.json poetry run python scripts/dump_openapi.py

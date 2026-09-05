.PHONY: help setup dev api web test check e2e clean corpus

# bin/ on Linux and macOS, Scripts/ on Windows.
PY := $(if $(wildcard backend/.venv/bin/python),backend/.venv/bin/python,backend/.venv/Scripts/python.exe)

help:
	@echo "setup   Install backend and frontend dependencies, build the demo corpus"
	@echo "api     Run the API on :8099"
	@echo "web     Run the frontend dev server on :5173"
	@echo "test    Run backend and frontend unit tests"
	@echo "e2e     Run the Playwright suite"
	@echo "check   Lint and type-check both sides"
	@echo "clean   Remove databases, caches and build output"

setup:
	cd backend && ./setup.sh
	cd frontend && npm install
	cd frontend && npx playwright install chromium

api:
	cd backend && ./run.sh

web:
	cd frontend && npm run dev

dev:
	@echo "Run 'make api' and 'make web' in two terminals."

corpus:
	$(PY) -m app.corpus.build

test:
	cd backend && ../$(PY) -m pytest
	cd frontend && npm test

e2e:
	cd frontend && npm run e2e

check:
	cd backend && ../$(PY) -m ruff check app tests
	cd backend && ../$(PY) -m mypy app
	cd frontend && npm run typecheck
	cd frontend && npm run lint

clean:
	rm -rf backend/data/*.db backend/data/*.db-* backend/data/httpcache backend/data/exports
	rm -rf backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache backend/htmlcov
	rm -rf frontend/dist frontend/playwright-report frontend/test-results
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

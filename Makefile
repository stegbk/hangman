.PHONY: install backend frontend test lint typecheck verify clean

# Port overrides. Default to the canonical 8000 / 3000; override on the command
# line when those are occupied (e.g. SSH tunnel on 8000):
#   make backend HANGMAN_BACKEND_PORT=8002
#   make frontend HANGMAN_BACKEND_PORT=8002 HANGMAN_FRONTEND_PORT=3001
# vite.config.ts and playwright.config.ts read the same env vars.
HANGMAN_BACKEND_PORT ?= 8000
HANGMAN_FRONTEND_PORT ?= 3000

install:
	cd backend && uv sync
	cd backend && uv pip install -e .
	cd frontend && pnpm install
	cd frontend && pnpm exec playwright install chromium

backend:
	cd backend && uv run uvicorn hangman.main:app --reload --host 127.0.0.1 --port $(HANGMAN_BACKEND_PORT)

frontend:
	cd frontend && HANGMAN_BACKEND_PORT=$(HANGMAN_BACKEND_PORT) HANGMAN_FRONTEND_PORT=$(HANGMAN_FRONTEND_PORT) pnpm dev

test:
	cd backend && uv run pytest
	cd frontend && pnpm test -- --run

lint:
	cd backend && uv run ruff check .
	cd frontend && pnpm lint

typecheck:
	cd backend && uv run mypy src/hangman
	cd frontend && pnpm tsc --noEmit -p tsconfig.app.json

verify: lint typecheck test

clean:
	rm -rf backend/.venv backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache
	rm -rf frontend/node_modules frontend/dist frontend/playwright-report
	rm -f backend/hangman.db

.PHONY: install backend backend-test frontend bdd test lint typecheck verify clean bdd-dashboard

# Port overrides. Default to the canonical 8000 / 3000; override on the command
# line when those are occupied (e.g. SSH tunnel on 8000):
#   make backend HANGMAN_BACKEND_PORT=8002
#   make frontend HANGMAN_BACKEND_PORT=8002 HANGMAN_FRONTEND_PORT=3001
# vite.config.ts and playwright.config.ts read the same env vars.
HANGMAN_BACKEND_PORT ?= 8000
HANGMAN_FRONTEND_PORT ?= 3000

# Auto-load .env for tools that expect env vars (e.g. ANTHROPIC_API_KEY for
# bdd-dashboard). `-include` is silent if missing; `export` propagates the
# loaded variables to child recipes (cd backend && uv run ...). The file is
# gitignored.
-include .env
export

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
	cd frontend && pnpm test:run

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

# BDD test-mode backend: isolated SQLite file (so BDD runs never touch the
# production hangman.db) + test-mode word pool (one-word "cat" per category).
backend-test:
	cd backend && \
	HANGMAN_WORDS_FILE=words.test.txt \
	HANGMAN_DB_URL=sqlite:///$(CURDIR)/backend/hangman.test.db \
	uv run uvicorn hangman.main:app --host 127.0.0.1 --port $(HANGMAN_BACKEND_PORT)

bdd:
	cd frontend && \
	HANGMAN_BACKEND_PORT=$(HANGMAN_BACKEND_PORT) \
	HANGMAN_FRONTEND_PORT=$(HANGMAN_FRONTEND_PORT) \
	pnpm bdd

.PHONY: bdd-dashboard
bdd-dashboard:  ## Generate the BDD quality dashboard (requires ANTHROPIC_API_KEY in env or .env)
	@if [ -z "$$ANTHROPIC_API_KEY" ]; then \
	  echo "ERROR: ANTHROPIC_API_KEY not set. Put 'ANTHROPIC_API_KEY=sk-ant-...' in .env (gitignored) or export it in your shell."; \
	  exit 2; \
	fi
	cd backend && uv run python -m tools.dashboard \
	  --model $(or $(MODEL),claude-sonnet-4-6) \
	  --max-workers $(or $(MAX_WORKERS),6)

.PHONY: install backend frontend test lint typecheck verify clean

install:
	cd backend && uv sync
	cd backend && uv pip install -e .
	cd frontend && pnpm install
	cd frontend && pnpm exec playwright install chromium

backend:
	cd backend && uv run uvicorn hangman.main:app --reload --host 127.0.0.1 --port 8000

frontend:
	cd frontend && pnpm dev

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

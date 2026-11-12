.PHONY: up down logs migrate test test-backend test-frontend lint check

up:            ## Start the development stack
	cp -n .env.example .env 2>/dev/null || true
	docker compose up --build -d
down:
	docker compose down
logs:
	docker compose logs -f backend frontend
migrate:
	docker compose exec backend alembic upgrade head
seed-dev-users: ## DEVELOPMENT ONLY: one test account per role (printed once)
	docker compose exec backend python -m app.cli seed-dev-users
create-director: ## First Director account (deployment)
	docker compose exec backend python -m app.cli create-director --email "$(EMAIL)" --name "$(NAME)"

test-backend:  ## Unit + integration tests against the dev Postgres/Redis
	docker compose exec -e TEST_DATABASE_URL=postgresql+psycopg://aven:aven_dev_password@postgres:5432/aven_test \
	  -e TEST_REDIS_URL=redis://redis:6379/1 backend pytest
test-frontend:
	docker compose exec frontend npm test
test: test-backend test-frontend

lint:
	docker compose exec backend sh -c "ruff check . && ruff format --check . && mypy app"
	docker compose exec frontend sh -c "npm run lint && npm run typecheck && npm run format:check"
check: lint test

.PHONY: dev build test reset-db backend frontend telegram logs down clean package setup

setup:
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env from .env.example"; fi

dev: setup
	docker compose up --build

build:
	docker compose build

test: setup
	docker compose run --rm -e USE_MOCK_LLM=true backend python -m pytest -q

reset-db: setup
	docker compose run --rm backend python -m app.db.reset_db

migrate: setup
	docker compose run --rm backend alembic upgrade head

migration: setup
	docker compose run --rm backend alembic revision --autogenerate -m "$(name)"

scheduler: setup
	cd backend && python -m app.scheduler.scheduler_worker

migrate-docker: setup
	docker compose run --rm backend alembic upgrade head

migration-docker: setup
	docker compose run --rm backend alembic revision --autogenerate -m "$(name)"

scheduler-docker: setup
	docker compose run --rm backend python -m app.scheduler.scheduler_worker

backend: setup
	docker compose up --build backend

frontend: setup
	docker compose up --build frontend

telegram: setup
	docker compose run --rm telegram-worker

logs:
	docker compose logs -f

down:
	docker compose down

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name ".pytest_cache" -type d -prune -exec rm -rf {} +
	find . -name "__MACOSX" -type d -prune -exec rm -rf {} +
	find . -name ".DS_Store" -delete
	rm -rf frontend/dist
	rm -rf backend/.pytest_cache
	rm -rf backend/venv
	rm -rf backend/.venv

package: clean
	rm -f ../yuno-agent-studio-final.zip
	cd .. && zip -r yuno-agent-studio-final.zip yuno-agent-studio \
		-x "*/.git/*" "*/.pytest_cache/*" "*/venv/*" "*/.venv/*" "*/node_modules/*" "*/__pycache__/*" "*.pyc" "*.db" "*/dist/*" "*/.env" "*/__MACOSX/*" "*/.DS_Store"

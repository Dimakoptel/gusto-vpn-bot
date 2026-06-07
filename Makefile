.PHONY: dev prod stop logs backup migrate

dev:
	docker-compose -f docker/docker-compose.yml up --build

prod:
	./scripts/deploy.sh

stop:
	docker-compose -f docker/docker-compose.yml down
	docker-compose -f docker/docker-compose.prod.yml down

logs:
	docker-compose -f docker/docker-compose.prod.yml logs -f gusto-bot gusto-backend

backup:
	docker-compose -f docker/docker-compose.prod.yml exec gusto-backend python -m app.tasks.backup_runner

migrate:
	docker-compose -f docker/docker-compose.yml exec gusto-backend alembic upgrade head

shell:
	docker-compose -f docker/docker-compose.yml exec gusto-backend bash

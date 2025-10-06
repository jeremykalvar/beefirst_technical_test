COMPOSE := docker compose
COMPOSE_DEV := docker-compose.yml
COMPOSE_TEST := docker-compose.test.yml
DC := $(COMPOSE) -f $(COMPOSE_DEV)
DCT := $(COMPOSE) -f $(COMPOSE_DEV) -f $(COMPOSE_TEST)
BASE_CONTAINER_NAME := beefirst_technical_test

.PHONY: compose-up build-api wait-db migrate test test-all test-ci down log-api

up:
	$(DC) up -d
	@echo "Services up."

build:
	$(DC) build

build-api:
	$(DC) build api

down:
	$(DC) down -v

stop:
	$(DC) stop

wait-db:
	$(DC) run --rm -T api ./scripts/wait-for.sh db:5432 -t 30

migrate:
	$(DC) run --rm -T api python -m app.infrastructure.db.migrate up

migration:
	$(DC) run --rm -T api python -m app.infrastructure.db.migrate new $(name)

logs:
	docker logs $(BASE_CONTAINER_NAME)-$(s)-1 -f

test:
	# run tests from the image, no bind mounts (via test override)
	$(DCT) run --rm -T api pytest -q

test-all: compose-up build-api wait-db migrate test

# convenience: a single entrypoint for CI
test-ci: test-all


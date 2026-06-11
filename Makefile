# BeeCall container management
#
# Image tags match what docker-compose.yaml expects, so `make build && make up`
# rebuilds local images and re-runs the stack without further config.
#
# Compose files:
#   docker-compose.yaml         — production: api + ui + infra + nginx/turn/…
#   docker-compose-local.yaml   — local dev: api + ui + infra (postgres/redis/minio).
#                                 The api container runs uvicorn + arq workers +
#                                 ari_manager + campaign_orchestrator via
#                                 scripts/start_services_docker.sh; nothing
#                                 needs to run on the host.
#
# Network:
#   All services join `beecall-network` (explicit, no project prefix), so
#   ad-hoc containers can `--network beecall-network` to talk to the stack.

REGISTRY ?= dograhai
TAG      ?= latest

API_IMAGE := $(REGISTRY)/dograh-api:$(TAG)
UI_IMAGE  := $(REGISTRY)/dograh-ui:$(TAG)

# Default service for logs (override: `make logs SERVICE=ui`)
SERVICE ?=

# INSECURE=1 enables --build-arg INSECURE_BUILD=1 in image builds, which
# turns off TLS verification for pip / npm / curl / nltk. Use only behind a
# corporate MITM proxy. The resulting runtime image still runs with the
# default secure posture; this only affects the build stage.
INSECURE ?=
BUILD_ARGS := $(if $(INSECURE),--build-arg INSECURE_BUILD=1,)

.PHONY: help build build-api build-ui \
        up up-local down down-local \
        restart restart-local rebuild rebuild-local \
        pull pull-local \
        logs logs-local ps ps-local clean

help:
	@echo "Container management targets:"
	@echo ""
	@echo "  Build:"
	@echo "    build         Build api and ui images locally"
	@echo "    build-api     Build api image only"
	@echo "    build-ui      Build ui image only"
	@echo ""
	@echo "  Run — production stack:"
	@echo "    up            Start production (api + ui + infra + nginx/turn/…)"
	@echo "    down          Stop production"
	@echo "    restart       down + up"
	@echo "    rebuild       build + restart           (refresh after code changes)"
	@echo "    pull          Pull latest images from registry (no rebuild)"
	@echo ""
	@echo "  Run — local dev stack:"
	@echo "    up-local      Start local dev (api + ui + infra)"
	@echo "    down-local    Stop local dev"
	@echo "    restart-local down-local + up-local"
	@echo "    rebuild-local build + restart-local     (refresh after code changes)"
	@echo "    pull-local    Pull latest images for local stack from registry"
	@echo ""
	@echo "  Inspect:"
	@echo "    ps            List production containers"
	@echo "    ps-local      List local dev containers"
	@echo "    logs          Tail production logs (SERVICE=name to filter)"
	@echo "    logs-local    Tail local dev logs (SERVICE=name to filter)"
	@echo ""
	@echo "  Maintain:"
	@echo "    clean         Prune stopped containers and dangling images"
	@echo ""
	@echo "  Variables (override on command line):"
	@echo "    REGISTRY=$(REGISTRY)  TAG=$(TAG)"
	@echo "    INSECURE=1  Disable TLS in build (corporate MITM proxy workaround)"

build: build-api build-ui

build-api:
	docker build $(BUILD_ARGS) -f api/Dockerfile -t $(API_IMAGE) .

build-ui:
	docker build $(BUILD_ARGS) -f ui/Dockerfile -t $(UI_IMAGE) .

up:
	docker compose up -d

up-local:
	docker compose -f docker-compose-local.yaml up -d

down:
	docker compose down

down-local:
	docker compose -f docker-compose-local.yaml down

restart: down up

restart-local: down-local up-local

rebuild: build restart

rebuild-local: build restart-local

pull:
	docker compose pull

pull-local:
	docker compose -f docker-compose-local.yaml pull

ps:
	docker compose ps

ps-local:
	docker compose -f docker-compose-local.yaml ps

logs:
	docker compose logs -f $(SERVICE)

logs-local:
	docker compose -f docker-compose-local.yaml logs -f $(SERVICE)

clean:
	docker container prune -f
	docker image prune -f

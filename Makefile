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

# PIPER_VOICES overrides which Piper voices are baked into the api image for the
# default in-process TTS — comma-separated ids from the rhasspy/piper-voices
# catalog, ~63 MB each. Empty means the Dockerfile default (ru_RU-irina-medium).
PIPER_VOICES ?=

BUILD_ARGS := $(if $(INSECURE),--build-arg INSECURE_BUILD=1,) \
              $(if $(PIPER_VOICES),--build-arg PIPER_VOICES=$(PIPER_VOICES),)

.PHONY: help build build-api build-ui build-asterisk \
        up up-local up-asterisk down down-local down-asterisk logs-asterisk \
        restart restart-local rebuild rebuild-local \
        pull pull-local \
        logs logs-local ps ps-local clean \
        test test-api test-api-unit test-api-ari test-ui test-env-setup

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
	@echo "  Run — Asterisk for telephony tests (opt-in, separate compose file):"
	@echo "    build-asterisk  Build Asterisk 22 + chan_websocket from source (slow)"
	@echo "    up-asterisk     Start Asterisk (brings up the local stack first)"
	@echo "    down-asterisk   Stop Asterisk"
	@echo "    logs-asterisk   Tail Asterisk logs"
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
	@echo "  Tests:"
	@echo "    test          Run api + ui test suites"
	@echo "    test-api      Run all api pytests against the *_test database"
	@echo "    test-api-unit Run api unit tests only (excludes -m slow)"
	@echo "    test-api-ari  Run api/tests/telephony/ari/ (ARI provider tests)"
	@echo "    test-ui       Run ui test scripts"
	@echo "    test-env-setup  Copy api/.env.test.example -> api/.env.test if missing"
	@echo "                    PYTEST_ARGS=-k name  to filter (api targets)"
	@echo ""
	@echo "  Variables (override on command line):"
	@echo "    REGISTRY=$(REGISTRY)  TAG=$(TAG)"
	@echo "    INSECURE=1  Disable TLS in build (corporate MITM proxy workaround)"
	@echo "    PIPER_VOICES=ru_RU-irina-medium,ru_RU-dmitri-medium"
	@echo "                Piper voices baked into the api image (~63 MB each)"

build: build-api build-ui

build-api:
	docker build $(BUILD_ARGS) -f api/Dockerfile -t $(API_IMAGE) .

build-ui:
	docker build $(BUILD_ARGS) -f ui/Dockerfile -t $(UI_IMAGE) .

up:
	docker compose up -d

up-local:
	docker compose -f docker-compose-local.yaml up -d

# Asterisk stays opt-in: its image is built from source (20+ min) and it
# publishes SIP/RTP host ports, so it has no place in the default local stack.
# Its compose file declares beecall-network as `external: true` — it joins the
# bridge the local stack creates — hence the up-local prerequisite.
build-asterisk:
	docker compose -f docker-compose-asterisk.yaml build

up-asterisk: up-local
	docker compose -f docker-compose-asterisk.yaml up -d

# Both compose files share the project name (the directory), so compose calls
# the local-stack containers "orphans" here and suggests --remove-orphans.
# Never add that flag: it would delete the whole local stack.
down-asterisk:
	docker compose -f docker-compose-asterisk.yaml down

logs-asterisk:
	docker compose -f docker-compose-asterisk.yaml logs -f

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

# ---------------------------------------------------------------------------
# Tests
#
# Conventions:
#   * api tests run pytest from the repo root with the venv activated and
#     api/.env.test sourced — api/conftest.py reads DATABASE_URL/REDIS_URL at
#     import time, so the env file must exist before pytest starts.
#   * test-env-setup creates api/.env.test from the committed example if it's
#     missing (the actual file is gitignored — per-developer).
#   * PYTEST_ARGS lets you pass through extra flags or -k filters, e.g.
#     `make test-api PYTEST_ARGS="-k extraction -x"`.
#   * Tests that need postgres/redis assume the local docker stack is up
#     (`make up-local`). Pure-unit tests don't, but the conftest still loads
#     env vars at import.
# ---------------------------------------------------------------------------

VENV_PY    := venv/bin/python
PYTEST_ARGS ?=

# Sources api/.env.test into the subshell that runs pytest. `set -a` exports
# every var defined while sourcing, then `set +a` stops auto-export so the
# rest of the command isn't polluted.
define run_pytest
	@if [ ! -f venv/bin/activate ]; then \
		echo "venv/ not found — run scripts/setup_local.sh first."; exit 1; \
	fi
	@$(MAKE) --no-print-directory test-env-setup
	@set -a && . api/.env.test && set +a && \
		$(VENV_PY) -m pytest $(1) $(PYTEST_ARGS)
endef

test: test-api test-ui

test-env-setup:
	@if [ ! -f api/.env.test ]; then \
		cp api/.env.test.example api/.env.test; \
		echo "Created api/.env.test from api/.env.test.example. Edit if your"; \
		echo "local postgres/redis bind on non-default ports."; \
	fi

test-api:
	$(call run_pytest,api/tests)

test-api-unit:
	$(call run_pytest,api/tests -m "not slow")

test-api-ari:
	$(call run_pytest,api/tests/telephony/ari)

test-ui:
	@if [ ! -d ui/node_modules ]; then \
		echo "ui/node_modules not found — running npm ci first…"; \
		cd ui && npm ci; \
	fi
	cd ui && npm test --if-present

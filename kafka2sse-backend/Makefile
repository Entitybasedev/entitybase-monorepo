.PHONY: help run clean stop build build-no-cache run-build-no-cache release test coverage

help:
	@echo "Available targets:"
	@echo "  make run               - Build and run the Docker container"
	@echo "  make stop              - Stop the running container"
	@echo "  make clean             - Remove stopped containers and build cache"
	@echo "  make build             - Build the Docker image"
	@echo "  make build-no-cache    - Build the Docker image without using cache"
	@echo "  make run-build-no-cache - Build without cache and run the container"
	@echo "  make release          - Create release: update version, commit, and tag (e.g., v2026.3.5)"
	@echo "  make test             - Run unit and contract tests"
	@echo "  make test-all          - Run all tests including integration"
	@echo "  make coverage         - Run tests with coverage report"

release:
	./scripts/run-release.sh

IMAGE_NAME=kafka2sse
CONTAINER_NAME=kafka2sse

run: build
	docker run -d --name $(CONTAINER_NAME) \
		-p 8888:8888 \
		-e KAFKA_BROKERS=$(KAFKA_BROKERS) \
		--network host \
		$(IMAGE_NAME)

stop:
	docker stop $(CONTAINER_NAME) 2>/dev/null || true
	docker rm $(CONTAINER_NAME) 2>/dev/null || true

clean:
	docker stop $(CONTAINER_NAME) 2>/dev/null || true
	docker rm $(CONTAINER_NAME) 2>/dev/null || true
	docker builder prune -f

build:
	docker build -t $(IMAGE_NAME) .

build-no-cache:
	docker build --no-cache -t $(IMAGE_NAME) .

run-build-no-cache: stop clean build-no-cache
	docker run -d --name $(CONTAINER_NAME) \
		-p 8888:8888 \
		-e KAFKA_BROKERS=$(KAFKA_BROKERS) \
		--network host \
		$(IMAGE_NAME)

test:
	poetry run pytest src/tests/unit/ src/tests/contract/ -v

test-all:
	poetry run pytest src/tests/ -v

coverage:
	poetry run pytest src/tests/unit/ src/tests/contract/ --cov=src --cov-report=term-missing --cov-report=html

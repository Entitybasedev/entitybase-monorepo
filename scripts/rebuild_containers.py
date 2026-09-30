#!/usr/bin/env python3
"""Rebuild Docker containers with their corresponding images and Dockerfiles."""

import argparse
import subprocess
import sys
from pathlib import Path

CONTAINER_MAP = {
    "create-tables": {
        "image": "entitybase-backend-create-tables:latest",
        "dockerfile": "libs/entitybase-backend/docker/containers/Dockerfile.create-tables",
        "context": "libs/entitybase-backend/",
    },
    "create-buckets": {
        "image": "entitybase-backend-create-buckets:latest",
        "dockerfile": "libs/entitybase-backend/docker/containers/Dockerfile.create-buckets",
        "context": "libs/entitybase-backend/",
    },
    "create-topics": {
        "image": "entitybase-backend-create-topics:latest",
        "dockerfile": "libs/entitybase-backend/docker/containers/Dockerfile.create-topics",
        "context": "libs/entitybase-backend/",
    },
    "api": {
        "image": "entitybase-api:latest",
        "dockerfile": "libs/entitybase-backend/docker/containers/Dockerfile.api",
        "context": "libs/entitybase-backend/",
        "service": "entitybase-api",
    },
    "idworker": {
        "image": "entitybase-backend-idworker:latest",
        "dockerfile": "libs/entitybase-backend/docker/containers/Dockerfile.idworker",
        "context": "libs/entitybase-backend/",
    },
    "json-worker": {
        "image": "entitybase-backend-json-worker:latest",
        "dockerfile": "libs/entitybase-backend/docker/containers/Dockerfile.json-worker",
        "context": "libs/entitybase-backend/",
    },
    "ttl-worker": {
        "image": "entitybase-backend-ttl-worker:latest",
        "dockerfile": "libs/entitybase-backend/docker/containers/Dockerfile.ttl-worker",
        "context": "libs/entitybase-backend/",
    },
    "stats-worker": {
        "image": "entitybase-backend-stats-worker:latest",
        "dockerfile": "libs/entitybase-backend/docker/containers/Dockerfile.stats-workers",
        "context": "libs/entitybase-backend/",
    },
    "elasticsearch-worker": {
        "image": "entitybase-backend-elasticsearch-worker:latest",
        "dockerfile": "libs/entitybase-backend/docker/containers/Dockerfile.api",
        "context": "libs/entitybase-backend/",
    },
    "meilisearch-worker": {
        "image": "entitybase-backend-meilisearch-worker:latest",
        "dockerfile": "libs/entitybase-backend/docker/containers/Dockerfile.api",
        "context": "libs/entitybase-backend/",
    },
    "purge-worker": {
        "image": "entitybase-backend-purge-worker:latest",
        "dockerfile": "libs/entitybase-backend/docker/containers/Dockerfile.purge-worker",
        "context": "libs/entitybase-backend/",
    },
    "incremental-rdf-worker": {
        "image": "entitybase-backend-incremental-rdf-worker:latest",
        "dockerfile": "libs/entitybase-backend/docker/containers/Dockerfile.incremental-rdf-worker",
        "context": "libs/entitybase-backend/",
    },
    "kafka2sse-backend": {
        "image": "kafka2sse-backend:latest",
        "dockerfile": "libs/kafka2sse-backend/Dockerfile",
        "context": "libs/kafka2sse-backend/",
        "service": "kafka2sse-backend",
    },
    "kafka2sse-frontend": {
        "image": "kafka2sse-frontend:latest",
        "dockerfile": "libs/kafka2sse-frontend/Dockerfile",
        "context": "libs/kafka2sse-frontend/",
        "service": "kafka2sse-frontend",
    },
}

ALL_CONTAINERS = list(CONTAINER_MAP.keys())


def run_command(cmd: list[str], check: bool = True, cwd: str | Path | None = None) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result


def pull_backend():
    """Pull latest changes from backend repository."""
    print("\n=== Pulling latest backend changes ===")
    run_command(["git", "pull"], check=False)
    backend_path = Path("libs/entitybase-backend")
    if backend_path.exists():
        run_command(["git", "pull"], cwd=backend_path, check=False)
    else:
        print("Warning: libs/entitybase-backend not found, skipping backend pull")


def export_requirements():
    """Export uv dependencies to requirements files for Docker builds."""
    print("\n=== Exporting requirements from pyproject.toml ===")
    backend_path = Path("libs/entitybase-backend")
    export_script = backend_path / "scripts" / "shell" / "export-requirements.sh"
    if export_script.exists():
        run_command(["bash", "scripts/shell/export-requirements.sh"], cwd=backend_path)
    else:
        print(f"Warning: {export_script} not found, skipping requirements export")


def build_image(image: str, dockerfile: str, context: str):
    """Build a Docker image."""
    print(f"\n=== Building {image} ===")
    cmd = [
        "docker", "build",
        "--no-cache",
        "-t", image,
        "-f", dockerfile,
        context,
    ]
    run_command(cmd)


def recreate_container(container: str, service: str | None = None):
    """Recreate a Docker Compose container."""
    service_name = service or container
    print(f"\n=== Recreating {container} ===")
    run_command(["docker", "compose", "rm", "-sf", service_name], check=False)
    run_command(["docker", "compose", "up", "-d", service_name])


def main():
    parser = argparse.ArgumentParser(
        description="Rebuild Docker containers with their images"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Rebuild all containers",
    )
    parser.add_argument(
        "containers",
        nargs="*",
        metavar="CONTAINER",
        help="Container name(s) to rebuild",
    )
    args = parser.parse_args()

    if not args.all and not args.containers:
        print("Error: Specify container names or use --all")
        print(f"Available containers: {', '.join(ALL_CONTAINERS)}")
        sys.exit(1)

    containers = args.containers if args.containers else ALL_CONTAINERS

    for container in containers:
        if container not in CONTAINER_MAP:
            print(f"Error: Unknown container '{container}'")
            print(f"Available: {', '.join(ALL_CONTAINERS)}")
            sys.exit(1)

    pull_backend()

    export_requirements()

    for container in containers:
        config = CONTAINER_MAP[container]
        build_image(config["image"], config["dockerfile"], config["context"])
        recreate_container(container, config.get("service"))

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
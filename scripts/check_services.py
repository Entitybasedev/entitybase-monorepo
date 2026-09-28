#!/usr/bin/env python3
"""Check service health status."""

import json
import subprocess
import sys
import urllib.request
from dataclasses import dataclass

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
NC = "\033[0m"

overall_status = 0


def run_docker_inspect(container: str, format_str: str) -> str:
    """Run docker inspect with given format and return output."""
    result = subprocess.run(
        ["docker", "inspect", "--format", format_str, container],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def get_container_state(container: str) -> str:
    """Get container state (running, exited, etc)."""
    return run_docker_inspect(container, "{{.State.Status}}")


def get_container_health(container: str) -> str:
    """Get container health status (healthy, unhealthy, empty)."""
    return run_docker_inspect(container, "{{.State.Health.Status}}")


def get_container_exit_code(container: str) -> str:
    """Get container exit code."""
    return run_docker_inspect(container, "{{.State.ExitCode}}")


def check_running_service(container: str) -> bool:
    """Check a running service container."""
    global overall_status
    
    state = get_container_state(container)
    
    if not state:
        print(f"{YELLOW}⚠️  {container} - not found{NC}")
        return True
    
    if state != "running":
        print(f"{RED}❌ {container} - {state}{NC}")
        return False
    
    health = get_container_health(container)
    
    if health == "healthy":
        print(f"{GREEN}✅ {container} - healthy{NC}")
        return True
    elif not health:
        print(f"{GREEN}✅ {container} - running{NC}")
        return True
    else:
        print(f"{RED}❌ {container} - {health}{NC}")
        return False


def check_completed_job(container: str) -> bool:
    """Check a completed job container."""
    global overall_status
    
    state = get_container_state(container)
    
    if not state:
        print(f"{YELLOW}⚠️  {container} - not found{NC}")
        return True
    
    exit_code = get_container_exit_code(container)
    
    if state == "exited" and exit_code == "0":
        print(f"{GREEN}✅ {container} - completed successfully{NC}")
        return True
    else:
        print(f"{RED}❌ {container} - state: {state}, exit code: {exit_code}{NC}")
        return False


def check_api_producers() -> dict:
    """Fetch producer status from API health endpoint."""
    global overall_status
    
    api_state = get_container_state("entitybase-api")
    if api_state != "running":
        print(f"{YELLOW}⚠️  entitybase-api not running, skipping producer checks{NC}")
        return {}
    
    try:
        req = urllib.request.Request("http://localhost:8083/health")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            return data.get("producers", {})
    except Exception:
        print(f"{RED}❌ Failed to fetch health endpoint{NC}")
        overall_status = 1
        return {}


def check_producer(name: str, status: str) -> bool:
    """Check a single producer status."""
    global overall_status
    
    if status == "connected":
        print(f"{GREEN}✅ {name} - connected{NC}")
        return True
    elif status == "disconnected":
        print(f"{RED}❌ {name} - disconnected{NC}")
        overall_status = 1
        return False
    elif status == "not_configured":
        print(f"{YELLOW}⚠️  {name} - not configured{NC}")
        return True
    else:
        print(f"{RED}❌ {name} - unknown{NC}")
        overall_status = 1
        return False


def main():
    global overall_status
    
    print("=== Infrastructure ===")
    if not check_running_service("mysql"): overall_status = 1
    if not check_running_service("mysql-health"): overall_status = 1
    if not check_running_service("minio"): overall_status = 1
    if not check_running_service("redpanda"): overall_status = 1
    if not check_running_service("redpanda-health"): overall_status = 1
    if not check_running_service("valkey"): overall_status = 1
    if not check_running_service("valkey-health"): overall_status = 1
    
    print("\n=== Setup Jobs ===")
    if not check_completed_job("create-buckets"): overall_status = 1
    if not check_completed_job("create-tables"): overall_status = 1
    if not check_completed_job("create-topics"): overall_status = 1
    
    print("\n=== Core Services ===")
    if not check_running_service("entitybase-api"): overall_status = 1
    if not check_running_service("idworker"): overall_status = 1
    if not check_running_service("kafka2sse-backend"): overall_status = 1
    if not check_running_service("kafka2sse-frontend"): overall_status = 1
    if not check_running_service("orchestrator-frontend"): overall_status = 1
    
    print("\n=== Workers ===")
    if not check_running_service("json-dump-worker"): overall_status = 1
    if not check_running_service("ttl-dump-worker"): overall_status = 1
    if not check_running_service("purge-worker"): overall_status = 1
    if not check_running_service("backlink-stats-worker"): overall_status = 1
    if not check_running_service("general-stats-worker"): overall_status = 1
    if not check_running_service("user-stats-worker"): overall_status = 1
    
    print("\n=== Producers ===")
    producers = check_api_producers()
    if not check_producer("entity_change", producers.get("entity_change", "unknown")): overall_status = 1
    if not check_producer("entitydiff", producers.get("entitydiff", "unknown")): overall_status = 1
    if not check_producer("user_change", producers.get("user_change", "unknown")): overall_status = 1
    
    print("\n=== Elasticsearch ===")
    if not check_running_service("elasticsearch"): overall_status = 1
    if not check_running_service("elasticsearch-health"): overall_status = 1
    if not check_running_service("elasticsearch-indexer-worker"): overall_status = 1
    
    print("\n=== Meilisearch ===")
    if not check_running_service("meilisearch"): overall_status = 1
    if not check_running_service("meilisearch-health"): overall_status = 1
    if not check_running_service("meilisearch-indexer-worker"): overall_status = 1
    
    sys.exit(overall_status)


if __name__ == "__main__":
    main()
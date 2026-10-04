#!/usr/bin/env python3
"""Generate overview documentation for all workers."""

import ast
import re
from pathlib import Path
from typing import Dict, Any, List


# noinspection PyUnresolvedReferences
def extract_worker_info(worker_file: Path, repo_root: Path) -> Dict[str, Any]:
    """Extract information from a worker file."""
    info = {
        "class_name": "",
        "description": "",
        "location": str(worker_file.relative_to(repo_root)),
    }

    try:
        with open(worker_file, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)

        # Find the main worker class
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and "Worker" in node.name:
                info["class_name"] = node.name
                # Get docstring from the first string literal in the class body
                if node.body and isinstance(node.body[0], ast.Expr):
                    expr = node.body[0]
                    if isinstance(expr.value, ast.Constant) and isinstance(
                        expr.value.value, str
                    ):
                        docstring = expr.value.value
                        # Clean up the docstring
                        docstring = docstring.strip()
                        # Remove extra whitespace and normalize
                        docstring = re.sub(r"\n\s+", " ", docstring)
                        info["description"] = docstring
                break

    except Exception as e:
        print(f"Warning: Could not parse {worker_file}: {e}")

    return info


def extract_worker_settings() -> Dict[str, List[str]]:
    """Extract worker-related settings from settings.py."""
    settings_file = Path("src/models/config/settings.py")
    worker_settings = {
        "id_generation": [
            "`WORKER_ID`: Unique worker identifier (default: auto-generated)"
        ],
        "backlink_statistics_worker": [],
        "watchlist_consumer_worker": [
            "`kafka_bootstrap_servers`: Comma-separated list of Kafka broker addresses",
            '`kafka_topic`: Kafka topic for entity changes (default: "wikibase-entity-changes")',
        ],
    }

    try:
        with open(settings_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Look for worker-related settings
        lines = content.split("\n")

        for line in lines:
            line = line.strip()

            # Look for worker-related settings
            if "backlink_stats_" in line:
                match = re.match(r"(\w+):\s*[^=]+=\s*(.+)", line)
                if match:
                    setting_name, default_value = match.groups()
                    worker_settings["backlink_statistics_worker"].append(
                        f"`{setting_name}`: {default_value.strip()}"
                    )

    except Exception as e:
        print(f"Warning: Could not parse settings: {e}")

    return worker_settings


def generate_markdown(
    workers: Dict[str, Dict[str, Any]], settings: Dict[str, List[str]]
) -> str:
    """Generate markdown overview of workers."""
    lines = ["# Workers Overview\n"]

    # Sort workers by name
    sorted_workers = sorted(workers.items())

    for worker_name, info in sorted_workers:
        title = worker_name.removesuffix("_worker").replace("_", " ").title()
        lines.append(f"## {title} Worker\n")

        lines.append(f"**Class**: `{info['class_name']}`")
        lines.append(f"**Location**: `{info['location']}`")
        lines.append(f"**Purpose**: {info['description']}\n")

        # Add configuration if available
        worker_config = settings.get(worker_name, [])
        if worker_config:
            lines.append("**Configuration**:")
            for config in worker_config:
                lines.append(f"- {config}")
            lines.append("")

        lines.append("**Health Checks**: Available via worker health endpoint\n")

        # Add dependencies for specific workers
        if worker_name == "watchlist_consumer_worker":
            lines.append("**Dependencies**: Requires aiokafka for Kafka consumption.\n")

    return "\n".join(lines)


def main() -> None:
    """Main entry point."""
    # Each worker is a top-level directory next to the backend, e.g.
    # ../json_dump_worker/src/json_dump_worker/worker.py
    repo_root = Path("..")
    worker_dirs = sorted(
        path.name
        for path in repo_root.glob("*/src/*_worker")
        if path.is_dir()
    )

    if not worker_dirs:
        print("Error: No worker directories found")
        return

    workers = {}

    for worker_name in worker_dirs:
        source_dir = repo_root / worker_name / "src" / worker_name
        worker_file = source_dir / "worker.py"
        if not worker_file.exists():
            candidates = sorted(source_dir.glob("*.py"))
            if not candidates:
                continue
            worker_file = candidates[0]
        info = extract_worker_info(worker_file, repo_root)
        workers[worker_name] = info

    # Extract settings
    settings = extract_worker_settings()

    # Generate markdown
    markdown = generate_markdown(workers, settings)

    # Output to stdout (will be redirected by update-docs.sh)
    print(markdown)


if __name__ == "__main__":
    main()

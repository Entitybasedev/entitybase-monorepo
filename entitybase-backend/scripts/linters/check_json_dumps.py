#!/usr/bin/env python3
"""Linter to check for json.dumps wrapping model_dump() without mode='json'.

Pydantic models can hold values json.dumps cannot serialize (datetime, UUID,
Decimal). model_dump(mode="json") converts them first. Deterministic output for
hashing is fine and skipped: json.dumps(..., sort_keys=True) is a deliberate
canonical form, not model serialization.
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple

sys.path.append(str(Path(__file__).parent.resolve()))

from allowlist_utils import FUNCTION_SEPARATOR, is_node_allowed

MODEL_DUMP_JSON = "model_dump(mode='json')"
SORT_KEYS = "sort_keys=True"


class JsonDumpsChecker:
    """Finds json.dumps calls that may miss model_dump(mode='json').

    Walks the tree once, tracking the enclosing function so an allowlist entry
    can name it: line numbers move whenever anything above them is edited.
    """

    def __init__(self, source: str, file_path: str, allowlist: set):
        self.source = source
        self.file_path = file_path
        self.allowlist = allowlist
        self.violations: List[Tuple[str, str, int, str]] = []

    def check_tree(self, tree: ast.AST) -> None:
        """Check every json.dumps call in the module."""
        self._walk(tree, None)

    def _walk(self, node: ast.AST, owner: ast.AST | None) -> None:
        for child in ast.iter_child_nodes(node):
            child_owner = (
                child
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                else owner
            )
            self._check(child, child_owner)
            self._walk(child, child_owner)

    def _check(self, node: ast.AST, owner: ast.AST | None) -> None:
        if not self._is_json_dumps(node):
            return
        if self._is_exempt(node):
            return
        # An allowlist entry may name the enclosing function; module level
        # calls fall back to the line and whole-file forms
        subject = owner if owner is not None else node
        if is_node_allowed(self.file_path, subject, self.allowlist):
            return
        call_source = ast.get_source_segment(self.source, node) or ""
        owner_name = getattr(owner, "name", None) or "<module>"
        self.violations.append(
            (str(self.file_path), call_source, node.lineno, owner_name)
        )

    @staticmethod
    def _is_json_dumps(node: ast.AST) -> bool:
        """True for json.dumps(...) calls."""
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "dumps"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "json"
        )

    def _is_exempt(self, node: ast.Call) -> bool:
        """Skip canonical hashing output and already-correct model dumps."""
        call_source = ast.get_source_segment(self.source, node) or ""
        if SORT_KEYS in call_source:
            return True
        return 'mode="json"' in call_source or MODEL_DUMP_JSON in call_source


def check_file(file_path: Path, allowlist: set) -> List[Tuple[str, str, int, str]]:
    """Check a single Python file."""
    try:
        source = Path(file_path).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return [(str(file_path), f"Syntax error in {file_path}", 0, "")]
    except Exception as e:
        return [(str(file_path), f"Error processing {file_path}: {e}", 0, "")]

    checker = JsonDumpsChecker(source, str(file_path), allowlist)
    checker.check_tree(tree)
    return checker.violations


def load_allowlist() -> set:
    """Load the allowlist from config/linters/allowlists/custom/json-dumps.txt."""
    allowlist_path = Path("config/linters/allowlists/custom/json-dumps.txt")
    if not allowlist_path.exists():
        return set()
    with open(allowlist_path, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip() and not line.startswith("#")}


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python check_json_dumps.py <path>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Path {path} does not exist")
        sys.exit(1)

    allowlist = load_allowlist()
    violations: List[Tuple[str, str, int, str]] = []

    if path.is_file() and path.suffix == ".py":
        violations.extend(check_file(path, allowlist))
    elif path.is_dir():
        for py_file in path.rglob("*.py"):
            if "workers" in py_file.parts or "scripts" in py_file.parts:
                continue
            violations.extend(check_file(py_file, allowlist))

    if violations:
        print(f"Found {len(violations)} potentially problematic json.dumps usage:")
        print("")
        for file_path, call_source, line_no, owner in violations:
            print(f"{file_path}:{line_no}: {call_source}")
        print("")
        print(
            "Consider replacing json.dumps(model.model_dump()) with "
            "json.dumps(model.model_dump(mode='json')) for better JSON serialization."
        )
        print(
            "To allowlist violations, add these entries to "
            "config/linters/allowlists/custom/json-dumps.txt:"
        )
        for file_path, _, _, owner in violations:
            print(f"{file_path}{FUNCTION_SEPARATOR}{owner}")
        sys.exit(1)

    print(
        "No json.dumps violations found (all uses correctly use "
        "model_dump(mode='json') or are allowlisted)."
    )


if __name__ == "__main__":
    main()

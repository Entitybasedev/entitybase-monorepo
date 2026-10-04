"""Unit tests for the shared allowlist helpers.

Allowlist entries may name a function (`file.py::function_name`) instead of a
line number, because a line number moves whenever anything above it is edited.
"""

import ast
import sys

sys.path.insert(0, "scripts/linters")

from allowlist_utils import is_function_allowed, is_node_allowed  # noqa: E402

SOURCE = """
def allowed() -> dict:
    return {}

def not_allowed() -> dict:
    return {}
"""


def function_named(name: str) -> ast.FunctionDef:
    """The function definition called ``name`` in SOURCE."""
    functions = [
        node
        for node in ast.parse(SOURCE).body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    assert functions, f"{name} not found in fixture"
    return functions[0]


class TestIsFunctionAllowed:
    """A function name entry matches only that function in that file."""

    def test_matches_the_named_function(self):
        allowlist = {"src/app.py::allowed"}
        assert is_function_allowed("src/app.py", "allowed", allowlist) is True

    def test_does_not_match_another_function(self):
        allowlist = {"src/app.py::allowed"}
        assert is_function_allowed("src/app.py", "not_allowed", allowlist) is False

    def test_does_not_match_another_file(self):
        allowlist = {"src/app.py::allowed"}
        assert is_function_allowed("src/other.py", "allowed", allowlist) is False

    def test_ignores_line_entries(self):
        allowlist = {"src/app.py:3"}
        assert is_function_allowed("src/app.py", "allowed", allowlist) is False


class TestIsNodeAllowed:
    """A node is allowed by name, and line entries still work."""

    def test_function_name_entry_survives_a_line_shift(self):
        allowlist = {"src/app.py::allowed"}
        node = function_named("allowed")
        node.lineno += 500  # as if the file grew above it
        assert is_node_allowed("src/app.py", node, allowlist) is True

    def test_line_entry_still_matches_within_tolerance(self):
        node = function_named("allowed")
        allowlist = {f"src/app.py:{node.lineno}"}
        assert is_node_allowed("src/app.py", node, allowlist) is True

    def test_line_entry_beyond_tolerance_does_not_match(self):
        node = function_named("allowed")
        allowlist = {f"src/app.py:{node.lineno - 50}"}
        assert is_node_allowed("src/app.py", node, allowlist) is False

    def test_unlisted_function_is_not_allowed(self):
        node = function_named("not_allowed")
        assert is_node_allowed("src/app.py", node, {"src/app.py::allowed"}) is False

    def test_whole_file_entry_allows_everything(self):
        node = function_named("not_allowed")
        assert is_node_allowed("src/app.py", node, {"src/app.py"}) is True

"""Unit tests for the dict-return linter's allowlist handling."""

import sys
import textwrap
from pathlib import Path

sys.path.insert(0, "scripts/linters")

from check_dict_returns import check_file  # noqa: E402

VIOLATION = textwrap.dedent(
    """
    def returns_dict() -> dict:
        return {}


    async def returns_dict_too() -> dict[str, Any]:
        return {}


    def returns_model() -> SomeModel:
        return SomeModel()
    """
)


def write_source(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "sample.py"
    path.write_text(source)
    return path


class TestCheckFile:
    """Violations are reported unless allowlisted by name."""

    def test_reports_every_dict_return(self, tmp_path: Path):
        path = write_source(tmp_path, VIOLATION)

        violations = check_file(path, set())

        assert {name for name, _, _, _ in violations} == {
            "returns_dict",
            "returns_dict_too",
        }

    def test_allows_a_function_by_name(self, tmp_path: Path):
        path = write_source(tmp_path, VIOLATION)

        violations = check_file(path, {f"{path}::returns_dict"})

        assert [name for name, _, _, _ in violations] == ["returns_dict_too"]

    def test_allows_a_function_by_line(self, tmp_path: Path):
        path = write_source(tmp_path, VIOLATION)
        line = next(
            node.lineno
            for node in __import__("ast").parse(path.read_text()).body
            if getattr(node, "name", None) == "returns_dict"
        )

        violations = check_file(path, {f"{path}:{line}"})

        assert [name for name, _, _, _ in violations] == ["returns_dict_too"]

    def test_clean_file_has_no_violations(self, tmp_path: Path):
        path = write_source(tmp_path, "def f() -> int:\n    return 1\n")

        assert check_file(path, set()) == []

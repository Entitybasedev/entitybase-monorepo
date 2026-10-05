"""Unit tests for the json.dumps linter."""

import sys
import textwrap
from pathlib import Path

sys.path.insert(0, "scripts/linters")

from check_json_dumps import check_file  # noqa: E402

SOURCE = textwrap.dedent(
    """
    import json


    def dumps_plain_dict():
        return json.dumps({"a": 1})


    def dumps_canonical():
        return json.dumps({"a": 1}, sort_keys=True)


    def dumps_model():
        return json.dumps(model.model_dump())


    def dumps_model_json_mode():
        return json.dumps(model.model_dump(mode="json"))


    OTHER = json.dumps({"module": "level"})
    """
)


def write_source(tmp_path: Path, source: str = SOURCE) -> Path:
    path = tmp_path / "sample.py"
    path.write_text(source)
    return path


def owners(violations) -> list[str]:
    return [owner for _, _, _, owner in violations]


class TestCheckFile:
    """json.dumps calls are reported unless exempt or allowlisted."""

    def test_reports_plain_and_bare_model_dumps(self, tmp_path: Path):
        violations = check_file(write_source(tmp_path), set())

        # The function name is reported, not just a line number
        assert owners(violations) == ["dumps_plain_dict", "dumps_model", "<module>"]

    def test_skips_canonical_hash_output(self, tmp_path: Path):
        violations = check_file(write_source(tmp_path), set())

        assert "dumps_canonical" not in owners(violations)

    def test_skips_model_dump_with_json_mode(self, tmp_path: Path):
        violations = check_file(write_source(tmp_path), set())

        assert "dumps_model_json_mode" not in owners(violations)

    def test_allows_a_function_by_name(self, tmp_path: Path):
        path = write_source(tmp_path)

        violations = check_file(path, {f"{path}::dumps_plain_dict"})

        assert "dumps_plain_dict" not in owners(violations)
        assert "dumps_model" in owners(violations)

    def test_name_entry_survives_a_line_shift(self, tmp_path: Path):
        path = write_source(tmp_path)
        # Move the function down, as an edit above it would
        path.write_text("# padding\n" * 20 + path.read_text())

        violations = check_file(path, {f"{path}::dumps_plain_dict"})

        assert "dumps_plain_dict" not in owners(violations)

    def test_whole_file_entry_allows_everything(self, tmp_path: Path):
        path = write_source(tmp_path)

        assert check_file(path, {str(path)}) == []

    def test_clean_file_has_no_violations(self, tmp_path: Path):
        path = write_source(
            tmp_path, "import json\nX = json.dumps({'a': 1}, sort_keys=True)\n"
        )

        assert check_file(path, set()) == []

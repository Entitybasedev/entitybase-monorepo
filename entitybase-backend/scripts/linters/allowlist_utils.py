#!/usr/bin/env python3
"""
Shared utility functions for linters that work with allowlists.
"""

import ast
from pathlib import Path
from typing import Dict, List, Set

# Allowlist entries may name a function instead of a line number:
#   src/models/rest_api/main.py::get_openapi
# A line number moves as soon as anything above it is edited, which turns an
# unrelated change into a lint failure about a function nobody touched.
FUNCTION_SEPARATOR = "::"


def is_function_allowed(
    file_path: str | Path,
    func_name: str,
    allowlist: Set[str],
) -> bool:
    """Check if a function is allowed by name.

    Args:
        file_path: Path to the file being checked
        func_name: Name of the function being checked
        allowlist: Set of "file.py::function_name" strings

    Returns:
        True if an entry names this function in this file
    """
    path = str(file_path)
    for entry in allowlist:
        if FUNCTION_SEPARATOR not in entry:
            continue
        entry_file, _, entry_name = entry.partition(FUNCTION_SEPARATOR)
        if entry_file.strip() == path and entry_name.strip() == func_name:
            return True
    return False


def is_node_allowed(
    file_path: str | Path,
    node: ast.AST,
    allowlist: Set[str] | Dict[str, List[int]],
    tolerance: int = 2,
) -> bool:
    """Check if an AST node is allowed, by function name or by line.

    Prefer this over is_line_allowed in new linters: it keeps an allowlist
    entry valid when the surrounding file changes.

    Args:
        file_path: Path to the file being checked
        node: The function definition being checked
        allowlist: Set of "file.py::name" or "file.py:line" strings
        tolerance: Line tolerance used for line-based entries

    Returns:
        True if the node is allowed
    """
    func_name = getattr(node, "name", None)
    if func_name is not None and is_function_allowed(file_path, func_name, allowlist):
        return True
    return is_line_allowed(file_path, getattr(node, "lineno", 0), allowlist, tolerance)


def is_line_allowed(
    file_path: str | Path,
    line_no: int,
    allowlist: Set[str] | Dict[str, List[int]],
    tolerance: int = 2,
) -> bool:
    """Check if a line number is allowed within the given tolerance.

    Args:
        file_path: Path to the file being checked
        line_no: Line number being checked
        allowlist: Either a set of "file:line" strings or a dict mapping files to line numbers
        tolerance: Number of lines to allow as variance (default: 2)

    Returns:
        True if the line is allowed (exact match or within tolerance range), False otherwise
    """
    file_path_str = str(file_path)

    if isinstance(allowlist, dict):
        if file_path_str in allowlist:
            allowed_lines = allowlist[file_path_str]
            if not allowed_lines:
                return True
            return any(abs(line_no - allowed_line) <= tolerance for allowed_line in allowed_lines)
        return False

    if isinstance(allowlist, set):
        for entry in allowlist:
            if ":" in entry:
                parts = entry.split(":")
                if len(parts) >= 2:
                    entry_file = parts[0]
                    try:
                        entry_line = int(parts[-1])
                        if entry_file == file_path_str and abs(line_no - entry_line) <= tolerance:
                            return True
                    except ValueError:
                        continue
            elif entry == file_path_str:
                return True

    return False

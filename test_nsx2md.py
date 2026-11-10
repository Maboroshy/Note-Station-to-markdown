"""Unit tests for sanitise_path_string.

nsx2md.py runs its export on import (pandoc check, glob, input()), so the
function under test is extracted from the module source with ast and exec'd
in isolation instead of importing the module.
"""

import ast
import urllib
import urllib.parse
from pathlib import Path


def _load_sanitise():
    source = (Path(__file__).resolve().parent / "nsx2md.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "sanitise_path_string"
    )
    namespace = {"urllib": urllib}
    exec(ast.get_source_segment(source, node), namespace)
    return namespace["sanitise_path_string"]


sanitise_path_string = _load_sanitise()


def test_illegal_chars_replaced():
    assert sanitise_path_string("a/b:c") == "a-b-c"


def test_trailing_dot_stripped():
    assert sanitise_path_string("Quarterly report.") == "Quarterly report"


def test_trailing_space_and_dot_stripped():
    assert sanitise_path_string("Quarterly report. ") == "Quarterly report"


def test_leading_space_stripped():
    assert sanitise_path_string("  draft") == "draft"


def test_normal_name_unchanged():
    assert sanitise_path_string("my-note_2024") == "my-note_2024"


def test_truncation_kept():
    assert sanitise_path_string("x" * 60) == "x" * 50

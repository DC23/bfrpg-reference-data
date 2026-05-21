"""Shared pytest fixtures and fixture-file test infrastructure."""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.odt_parser import OdtParser

ODT_PATH = Path(__file__).parent.parent / 'data' / 'Basic-Fantasy-RPG-Rules-r142.odt'
FIXTURES_DIR = Path(__file__).parent / 'fixtures'


# ---------------------------------------------------------------------------
# Parser session fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope='session')
def parser() -> OdtParser:
    return OdtParser(ODT_PATH)


@pytest.fixture(scope='session')
def walk_events(parser: OdtParser) -> list[tuple]:
    return list(parser.walk())


# ---------------------------------------------------------------------------
# YAML fixture loading
# ---------------------------------------------------------------------------

def load_fixture(filename: str) -> list[dict]:
    """Load a YAML fixture file from tests/fixtures/."""
    path = FIXTURES_DIR / filename
    if not path.exists():
        return []
    with open(path) as f:
        data = yaml.safe_load(f)
    return data or []


# ---------------------------------------------------------------------------
# Field-level assertion helper
# ---------------------------------------------------------------------------

def assert_fields(
    actual: dict[str, Any],
    expected: dict[str, Any],
    context: str = '',
) -> None:
    """Assert only the fields present in expected; missing fields pass silently."""
    for key, exp_val in expected.items():
        assert key in actual, (
            f'{context}: field {key!r} missing from parsed output'
        )
        act_val = actual[key]
        assert act_val == exp_val, (
            f'{context}: field {key!r}: expected {exp_val!r}, got {act_val!r}'
        )


# ---------------------------------------------------------------------------
# Name lookup with closest-match hint
# ---------------------------------------------------------------------------

def find_by_name(
    items_by_name: dict[str, Any],
    name: str,
    entity_type: str = 'item',
) -> Any:
    """Return the item with exact name, or pytest.fail with closest-match hint."""
    if name in items_by_name:
        return items_by_name[name]
    candidates = difflib.get_close_matches(name, items_by_name.keys(), n=3, cutoff=0.6)
    hint = f' Closest matches: {candidates}' if candidates else ' No close matches found.'
    pytest.fail(f"{entity_type} {name!r} not found in parser output.{hint}")

"""Fixture-driven tests for extract_spells.py."""

from __future__ import annotations

import pytest

from conftest import assert_fields, find_by_name, load_fixture
from scripts.extract_spells import extract_spells


@pytest.fixture(scope="session")
def spells(walk_events):
    return extract_spells(list(walk_events))


# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------


def test_spell_count(spells):
    # 109 SpellHeadings minus 4 class-name entries = 105 spells
    assert len(spells) == 105


def test_no_class_name_entries(spells):
    for class_name in ("Cleric", "Fighter", "Magic-User", "Thief"):
        assert class_name not in spells, f"{class_name!r} should not appear as a spell"


# ---------------------------------------------------------------------------
# Fixture-driven field checks
# ---------------------------------------------------------------------------


def test_fixture_spells(spells):
    for entry in load_fixture("spells.yaml"):
        name = entry["name"]
        spell = find_by_name(spells, name, "spell")

        if "reversible" in entry:
            assert spell.get("reversible") == entry["reversible"], (
                f"{name}: wrong reversible flag"
            )

        if "range" in entry:
            assert spell.get("range") == entry["range"], (
                f"{name}: wrong range: expected {entry['range']!r}, got {spell.get('range')!r}"
            )

        if "duration" in entry:
            assert spell.get("duration") == entry["duration"], (
                f"{name}: wrong duration: expected {entry['duration']!r}, got {spell.get('duration')!r}"
            )

        if "classes" in entry:
            actual_classes = spell.get("classes", [])
            for exp_cls in entry["classes"]:
                match = next(
                    (
                        c for c in actual_classes
                        if c.get("class") == exp_cls["class"]
                        and c.get("level") == exp_cls["level"]
                    ),
                    None,
                )
                assert match is not None, (
                    f"{name}: class entry {exp_cls!r} not found in {actual_classes!r}"
                )

"""Fixture-driven tests for extract_monsters.py."""

from __future__ import annotations

from typing import Any

import pytest

from conftest import assert_fields, find_by_name, load_fixture
from scripts.extract_monsters import extract_monsters, load_config


@pytest.fixture(scope="session")
def monsters(walk_events):
    return extract_monsters(list(walk_events), load_config())


# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------


def test_monster_count(monsters):
    # 221 MonsterHeadings: 'Beasts of Burden' expands to 7 individual beasts,
    # Dragon and Elemental group intros are kept; net should be well over 220
    assert len(monsters) >= 220


def test_dragon_group_intro(monsters):
    assert "Dragon" in monsters
    d = monsters["Dragon"]
    assert d["type"] == "group_intro"
    assert d["group"] == "dragon"


def test_elemental_group_intro(monsters):
    assert "Elemental" in monsters
    assert monsters["Elemental"]["type"] == "group_intro"


def test_beasts_of_burden_not_in_output(monsters):
    assert "Beasts of Burden" not in monsters


def test_camel_split_from_beasts(monsters):
    assert "Camel" in monsters
    assert monsters["Camel"]["type"] == "monster"
    assert "stats" in monsters["Camel"]


# ---------------------------------------------------------------------------
# Fixture-driven field checks
# ---------------------------------------------------------------------------


def test_fixture_monsters(monsters):
    for entry in load_fixture("monsters.yaml"):
        name = entry["name"]
        entity = find_by_name(monsters, name, "monster")

        top_level = {
            k: v
            for k, v in entry.items()
            if k not in ("name", "stats", "variants", "age_categories")
        }
        assert_fields(entity, top_level, context=name)

        if "stats" in entry:
            assert "stats" in entity, f"{name}: expected top-level stats"
            assert_fields(entity["stats"], entry["stats"], context=f"{name}.stats")

        if "variants" in entry:
            assert "variants" in entity, f"{name}: expected variants"
            for vk, vfields in entry["variants"].items():
                assert vk in entity["variants"], f"{name}: variant {vk!r} missing"
                assert_fields(entity["variants"][vk], vfields, context=f"{name}.{vk}")

        if "age_categories" in entry:
            assert "age_categories" in entity, f"{name}: missing age_categories"
            _check_age_categories(
                entity["age_categories"], entry["age_categories"], name
            )


def _check_age_categories(actual: list[dict], expected: list[dict], name: str) -> None:
    actual_by_cat = {c["category"]: c for c in actual}
    for exp_cat in expected:
        cat_num = exp_cat["category"]
        assert cat_num in actual_by_cat, f"{name}: age category {cat_num!r} not found"
        _check_cat_fields(actual_by_cat[cat_num], exp_cat, f"{name}[cat={cat_num}]")


def _check_cat_fields(actual: dict, expected: dict[str, Any], context: str) -> None:
    for key, exp_val in expected.items():
        if key == "category":
            continue
        assert key in actual, f"{context}: field {key!r} missing"
        act_val = actual[key]
        if isinstance(exp_val, dict):
            assert isinstance(act_val, dict), f"{context}: {key!r} should be a dict"
            assert_fields(act_val, exp_val, context=f"{context}.{key}")
        else:
            assert (
                act_val == exp_val
            ), f"{context}: {key!r}: expected {exp_val!r}, got {act_val!r}"

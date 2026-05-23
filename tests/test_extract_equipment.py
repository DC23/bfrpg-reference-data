"""Fixture-driven tests for extract_equipment.py."""

from __future__ import annotations

import pytest

from conftest import assert_fields, load_fixture
from scripts.extract_equipment import extract_equipment


@pytest.fixture(scope="session")
def equipment(walk_events):
    return extract_equipment(list(walk_events))


# ---------------------------------------------------------------------------
# Sanity counts
# ---------------------------------------------------------------------------


def test_gear_count(equipment):
    # Two tables of 23 items each (header rows excluded)
    assert len(equipment["equipment"]) == 46


def test_armour_count(equipment):
    # No Armor, Leather, Chain Mail, Plate Mail, Shield
    assert len(equipment["armour"]) == 5


def test_weapon_categories(equipment):
    categories = [w["category"] for w in equipment["weapons"]]
    for expected in ("Axes", "Bows", "Daggers", "Swords", "Hammers and Maces", "Other Weapons"):
        assert expected in categories, f"Category {expected!r} missing from weapons"


def test_missile_range_count(equipment):
    assert len(equipment["missile_ranges"]) == 10


def test_vehicle_counts(equipment):
    assert len(equipment["vehicles"]["land"]) == 3
    assert len(equipment["vehicles"]["water"]) == 10


def test_siege_engine_count(equipment):
    assert len(equipment["siege_engines"]) == 6


# ---------------------------------------------------------------------------
# Fixture-driven: weapons
# ---------------------------------------------------------------------------


def _weapons_by_name(equipment) -> dict:
    return {w["name"]: w for w in equipment["weapons"]}


def test_fixture_weapons(equipment):
    lookup = _weapons_by_name(equipment)
    for entry in load_fixture("weapons.yaml"):
        name = entry["name"]
        assert name in lookup, f"Weapon {name!r} not found in extracted weapons"
        actual = lookup[name]
        assert_fields(actual, {k: v for k, v in entry.items() if k != "name"}, context=name)


# ---------------------------------------------------------------------------
# Fixture-driven: armour (includes shield)
# ---------------------------------------------------------------------------


def _armour_by_name(equipment) -> dict:
    return {a["name"]: a for a in equipment["armour"]}


def test_fixture_armour(equipment):
    lookup = _armour_by_name(equipment)
    for entry in load_fixture("armor.yaml"):
        name = entry["name"]
        assert name in lookup, f"Armour {name!r} not found"
        assert_fields(lookup[name], {k: v for k, v in entry.items() if k != "name"}, context=name)


def test_fixture_shields(equipment):
    lookup = _armour_by_name(equipment)
    for entry in load_fixture("shields.yaml"):
        name = entry["name"]
        assert name in lookup, f"Shield {name!r} not found in armour output"
        assert_fields(lookup[name], {k: v for k, v in entry.items() if k != "name"}, context=name)


# ---------------------------------------------------------------------------
# Fixture-driven: vehicles
# ---------------------------------------------------------------------------


def test_fixture_vehicles(equipment):
    fixture = load_fixture("vehicles.yaml")
    if not fixture:
        return

    land_by_name = {v["name"]: v for v in equipment["vehicles"]["land"]}
    water_by_name = {v["name"]: v for v in equipment["vehicles"]["water"]}

    for entry in fixture.get("land", []):
        name = entry["name"]
        assert name in land_by_name, f"Land vehicle {name!r} not found"
        assert_fields(land_by_name[name], {k: v for k, v in entry.items() if k != "name"}, context=name)

    for entry in fixture.get("water", []):
        name = entry["name"]
        assert name in water_by_name, f"Water vehicle {name!r} not found"
        assert_fields(water_by_name[name], {k: v for k, v in entry.items() if k != "name"}, context=name)

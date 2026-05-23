"""Extract equipment data from BFRPG ODT source to JSON files.

Run: python -m scripts.extract_equipment
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from scripts.odt_parser import OdtParser

ROOT = Path(__file__).parent.parent
ODT_PATH = ROOT / "data" / "Basic-Fantasy-RPG-Rules-r142.odt"
DATA_DIR = ROOT / "data" / "equipment"

# Section boundaries
_EQUIP_START_HEADING = "Cost of Weapons and Equipment"
_VEHICLES_HEADING = "Vehicles"
_SIEGE_HEADING = "Siege Engines"
_STOP_SECTION = "PART 3:  SPELLS"


# ---------------------------------------------------------------------------
# Table parsers
# ---------------------------------------------------------------------------


def _parse_gear_rows(rows: list[list[str]]) -> list[dict]:
    """Parse a gear table (Item / Price / Weight). Skips the header row."""
    items = []
    for row in rows[1:]:
        if len(row) < 3:
            continue
        name, price, weight = row[0], row[1], row[2]
        if name:
            items.append({"name": name, "price": price, "weight": weight})
    return items


def _parse_weapons_table(rows: list[list[str]]) -> list[dict]:
    """Parse the weapons table into a flat list.

    Tab depth in column 0 indicates structure:
      0 tabs = category header row (empty price/size/weight/damage)
      1 tab  = weapon
      2 tabs = sub-item (ammo or use-mode variant)

    Silver† weapons: † is stripped from the name and silver: true is set.
    Parent items with no inline damage (e.g. Shortbow, Spear) omit the
    damage field rather than emitting an empty string.
    """
    items = []
    current_category = ""
    current_parent = ""

    for row in rows[1:]:  # skip header
        raw_name = row[0]
        price = row[1] if len(row) > 1 else ""
        size = row[2] if len(row) > 2 else ""
        weight = row[3] if len(row) > 3 else ""
        damage = row[4] if len(row) > 4 else ""

        tab_depth = len(raw_name) - len(raw_name.lstrip("\t"))
        name = raw_name.lstrip("\t")
        silver = "†" in name
        name = name.replace("†", "").strip()

        if tab_depth == 0:
            current_category = name
            current_parent = ""
            continue

        item: dict[str, Any] = {"name": name, "category": current_category}

        if tab_depth == 2:
            item["parent"] = current_parent
        else:
            current_parent = name

        if price:
            item["price"] = price
        if size:
            item["size"] = size
        if weight:
            item["weight"] = weight
        if damage:
            item["damage"] = damage
        if silver:
            item["silver"] = True

        items.append(item)

    return items


def _parse_armour_table(rows: list[list[str]]) -> list[dict]:
    """Parse armour+shield table (Armor Type / Price / Weight / AC)."""
    items = []
    for row in rows[1:]:
        if len(row) < 4:
            continue
        items.append({"name": row[0], "price": row[1], "weight": row[2], "ac": row[3]})
    return items


def _parse_missile_ranges(rows: list[list[str]]) -> list[dict]:
    """Parse missile weapon ranges table."""
    items = []
    for row in rows[1:]:
        if len(row) < 4:
            continue
        # Header col 3 contains a newline: 'Long\n(-2)' — normalise for the key name,
        # preserve raw value in the dict.
        items.append({
            "weapon": row[0],
            "short": row[1],
            "medium": row[2],
            "long": row[3],
        })
    return items


def _normalize_header(text: str) -> str:
    """Normalise a table header cell to a snake_case key.

    Collapses whitespace/newlines, strips footnote markers (*) and
    parenthetical suffixes like (gp), (+1), (-2), then lowercases and
    replaces non-alphanumeric runs with underscores.
    """
    text = re.sub(r"\s+", " ", text).strip().replace("*", "")
    text = re.sub(r"\s*\([^)]*\)", "", text).strip()
    text = re.sub(r"[^a-z0-9]+", "_", text.lower())
    return text.strip("_")


def _parse_headed_table(rows: list[list[str]]) -> list[dict]:
    """Parse any table whose first row is the header.

    The first column is always mapped to 'name' regardless of header text,
    for consistency with other extractor outputs. Empty-name rows are skipped.
    """
    if not rows:
        return []
    headers = [_normalize_header(h) for h in rows[0]]
    if headers:
        headers[0] = "name"
    items = []
    for row in rows[1:]:
        item = dict(zip(headers, row))
        if item.get("name"):
            items.append(item)
    return items


def _parse_land_vehicles(rows: list[list[str]]) -> list[dict]:
    return _parse_headed_table(rows)


def _parse_water_vehicles(rows: list[list[str]]) -> list[dict]:
    """Parse the water vehicle table.

    Row 0 is the header. The 'Movement' column spans two physical columns:
    col 4 holds the base speed and col 5 holds the maneuverability value
    (which has an empty string header).
    """
    items = []
    for row in rows[1:]:
        if len(row) < 9 or not row[0]:
            continue
        items.append({
            "name": row[0],
            "size": row[1],
            "cargo": row[2],
            "crew": row[3],
            "movement": row[4],
            "maneuverability": row[5],
            "miles_per_day": row[6],
            "hardness_hp": row[7],
            "cost": row[8],
        })
    return items


def _parse_siege_engines(rows: list[list[str]]) -> list[dict]:
    return _parse_headed_table(rows)


# ---------------------------------------------------------------------------
# Event routing
# ---------------------------------------------------------------------------


def _collect_equipment_events(events: list[tuple]) -> dict[str, list]:
    """Walk events and bucket tables by section heading.

    Returns a dict of section name → list of table row-lists.
    """
    buckets: dict[str, list] = {
        "Equipment": [],
        "Weapons": [],
        "Missile Weapon Ranges": [],
        "Armor and Shields": [],
        "Land Transportation": [],
        "Water Transportation": [],
        "Siege Engines": [],
    }

    in_section = False
    current_sub = ""

    for event in events:
        kind = event[0]

        if kind != "p" and kind != "table":
            continue

        if kind == "p":
            _, style, text = event
            if style == "MainHeading" and text == _EQUIP_START_HEADING:
                in_section = True
                current_sub = ""
                continue
            if style == "SectionHeading" and text == _STOP_SECTION:
                break
            if not in_section:
                continue
            if style in ("MainHeading", "SubHeading"):
                current_sub = text

        elif kind == "table" and in_section:
            _, _tname, rows = event
            if current_sub in buckets:
                buckets[current_sub].append(rows)

    return buckets


# ---------------------------------------------------------------------------
# Main extraction function
# ---------------------------------------------------------------------------


def extract_equipment(events: list[tuple]) -> dict[str, Any]:
    """Return a dict with keys: equipment, weapons, armour, missile_ranges, vehicles, siege_engines."""
    buckets = _collect_equipment_events(events)

    equipment: list[dict] = []
    for table_rows in buckets["Equipment"]:
        equipment.extend(_parse_gear_rows(table_rows))

    weapons: list[dict] = []
    for table_rows in buckets["Weapons"]:
        weapons.extend(_parse_weapons_table(table_rows))

    armour: list[dict] = []
    for table_rows in buckets["Armor and Shields"]:
        armour.extend(_parse_armour_table(table_rows))

    missile_ranges: list[dict] = []
    for table_rows in buckets["Missile Weapon Ranges"]:
        missile_ranges.extend(_parse_missile_ranges(table_rows))

    land_vehicles: list[dict] = []
    for table_rows in buckets["Land Transportation"]:
        land_vehicles.extend(_parse_land_vehicles(table_rows))

    water_vehicles: list[dict] = []
    for table_rows in buckets["Water Transportation"]:
        water_vehicles.extend(_parse_water_vehicles(table_rows))

    siege_engines: list[dict] = []
    for table_rows in buckets["Siege Engines"]:
        siege_engines.extend(_parse_siege_engines(table_rows))

    return {
        "equipment": equipment,
        "weapons": weapons,
        "armour": armour,
        "missile_ranges": missile_ranges,
        "vehicles": {"land": land_vehicles, "water": water_vehicles},
        "siege_engines": siege_engines,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = OdtParser(ODT_PATH)
    events = list(parser.walk())
    data = extract_equipment(events)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for key in ("equipment", "weapons", "armour", "missile_ranges", "siege_engines"):
        out_path = DATA_DIR / f"{key}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data[key], f, indent=2, ensure_ascii=False)
        print(f"Wrote {len(data[key])} entries to {out_path}")

    vehicles_path = DATA_DIR / "vehicles.json"
    with open(vehicles_path, "w", encoding="utf-8") as f:
        json.dump(data["vehicles"], f, indent=2, ensure_ascii=False)
    total_v = len(data["vehicles"]["land"]) + len(data["vehicles"]["water"])
    print(f"Wrote {total_v} vehicles to {vehicles_path}")


if __name__ == "__main__":
    main()

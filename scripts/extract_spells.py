"""Extract spell data from BFRPG ODT source to per-spell JSON files.

Run: python -m scripts.extract_spells
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from scripts.odt_parser import OdtParser

ROOT = Path(__file__).parent.parent
ODT_PATH = ROOT / "data" / "Basic-Fantasy-RPG-Rules-r142.odt"
DATA_DIR = ROOT / "data" / "spells"

_SPELL_HEADING = "SpellHeading"
_SPELL_MID = "SpellMidHeading"
_SPELL_SUB = "SpellSubHeading"
_SECTION_STOP = "SectionHeading"
_PART4_TEXT = "PART 4:  THE ADVENTURE"

# These four names reuse SpellHeading style but are chapter dividers, not spells.
_CLASS_NAMES = frozenset({"Cleric", "Fighter", "Magic-User", "Thief"})


# ---------------------------------------------------------------------------
# Heading parsers
# ---------------------------------------------------------------------------


def parse_spell_heading(text: str) -> tuple[str, bool, str] | None:
    """Parse a SpellHeading line.

    Two formats exist in the source:
    - Standard: '{name}[*]\\tRange:\\t{range}' — range is inline
    - Split:    '{name}[*]'                   — range is in the following SpellMidHeading

    Returns (canonical_name, reversible, inline_range) or None for class-name dividers.
    """
    if "\t" in text:
        name_part, _, range_val = text.partition("\tRange:\t")
    else:
        name_part, range_val = text, ""

    reversible = name_part.endswith("*")
    name = name_part.rstrip("*").strip()
    if name in _CLASS_NAMES:
        return None
    return name, reversible, range_val.strip()


# ---------------------------------------------------------------------------
# Block collection
# ---------------------------------------------------------------------------


def _collect_blocks(events: list[tuple]) -> list[tuple[str, bool, str, list[tuple]]]:
    """Collect one block per spell.

    Returns list of (name, reversible, inline_range, block_events).
    Stops at the PART 4 SectionHeading. Filters class-name dividers.
    """
    blocks: list[tuple[str, bool, str, list[tuple]]] = []
    current: tuple[str, bool, str] | None = None
    current_events: list[tuple] = []

    for event in events:
        kind = event[0]

        if kind == "p" and event[1] == _SECTION_STOP and event[2] == _PART4_TEXT:
            break

        if kind == "p" and event[1] == _SPELL_HEADING:
            if current is not None:
                blocks.append((*current, current_events))
            parsed = parse_spell_heading(event[2])
            current = parsed
            current_events = []
            continue

        if current is not None:
            current_events.append(event)

    if current is not None:
        blocks.append((*current, current_events))

    return blocks


# ---------------------------------------------------------------------------
# Block processing
# ---------------------------------------------------------------------------


def _extract_spell_meta(
    events: list[tuple], inline_range: str
) -> tuple[list[dict], str, str]:
    """Return (classes, range_val, duration) from block events.

    Handles two formats:
    - Standard: SpellSubHeading has '{class} {level}' on left; range is already inline.
    - Split:    SpellMidHeading has '{class} {level}\\tRange:\\t{range}';
                SpellSubHeading has '\\tDuration:\\t{duration}' (empty class part).
    """
    classes: list[dict] = []
    range_val = inline_range
    duration = ""

    for event in events:
        if event[0] != "p":
            continue
        style, text = event[1], event[2]

        if style == _SPELL_MID:
            class_part, _, r = text.partition("\tRange:\t")
            class_part = class_part.strip()
            if class_part:
                m = re.match(r"^(.+?)\s+(\d+)$", class_part)
                if m:
                    classes.append({"class": m.group(1), "level": int(m.group(2))})
            if r:
                range_val = r.strip()

        elif style == _SPELL_SUB:
            class_part, _, dur = text.partition("\tDuration:\t")
            class_part = class_part.strip()
            if class_part:
                for segment in class_part.split(", "):
                    segment = segment.strip()
                    m = re.match(r"^(.+?)\s+(\d+)$", segment)
                    if m:
                        classes.append({"class": m.group(1), "level": int(m.group(2))})
            duration = dur.strip()

    return classes, range_val, duration


def _extract_description(events: list[tuple]) -> list[Any]:
    """Collect description content: body paragraphs, embedded tables, embedded lists."""
    _meta_styles = {_SPELL_SUB, _SPELL_HEADING, _SPELL_MID}
    description: list[Any] = []
    for event in events:
        if event[0] == "p" and event[1] not in _meta_styles:
            text = event[2].strip()
            if text:
                description.append(text)
        elif event[0] == "table":
            description.append({"table": event[2]})
        elif event[0] == "list":
            description.append({"list": event[1]})
    return description


def process_block(
    name: str,
    reversible: bool,
    inline_range: str,
    events: list[tuple],
) -> dict[str, Any]:
    classes, range_val, duration = _extract_spell_meta(events, inline_range)
    description = _extract_description(events)

    spell: dict[str, Any] = {"name": name}
    if reversible:
        spell["reversible"] = True
    spell["classes"] = classes
    spell["range"] = range_val
    spell["duration"] = duration
    if description:
        spell["description"] = description
    return spell


# ---------------------------------------------------------------------------
# Main extraction function
# ---------------------------------------------------------------------------


def extract_spells(events: list[tuple]) -> dict[str, dict]:
    """Return {spell_name: spell_dict} for all spells in the document."""
    results: dict[str, dict] = {}
    for block in _collect_blocks(events):
        name, reversible, inline_range, block_events = block
        if name is None:
            continue
        spell = process_block(name, reversible, inline_range, block_events)
        results[spell["name"]] = spell
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _make_slug(name: str) -> str:
    clean = re.sub(r"[^\w\s-]", "", name.lower())
    return re.sub(r"[\s_]+", "-", clean).strip("-")


def main() -> None:
    parser = OdtParser(ODT_PATH)
    events = list(parser.walk())
    spells = extract_spells(events)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, spell in spells.items():
        filename = f"{_make_slug(name)}.json"
        with open(DATA_DIR / filename, "w", encoding="utf-8") as f:
            json.dump(spell, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(spells)} spells to {DATA_DIR}")


if __name__ == "__main__":
    main()

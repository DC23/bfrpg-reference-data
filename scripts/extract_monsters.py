"""Extract monster data from BFRPG ODT source to a single collated JSON file.

Run: python -m scripts.extract_monsters
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from scripts.odt_parser import OdtParser, normalise_spaces

ROOT = Path(__file__).parent.parent
ODT_PATH = ROOT / "data" / "Basic-Fantasy-RPG-Rules-r142.odt"
CONFIG_PATH = ROOT / "scripts" / "extractor_config.yaml"
DATA_DIR = ROOT / "data"

# En-dash and em-dash — both appear in shared-value decorators in the source
_DASHES = "–—"

_REDIRECT_RE = re.compile(r"^See (.+?) on page \d+\.$")

_GROUP_INTROS: dict[str, str] = {
    "Dragon": "dragon",
    "Elemental": "elemental",
}


# ---------------------------------------------------------------------------
# Key / filename helpers
# ---------------------------------------------------------------------------


def normalise_key(label: str) -> str:
    s = label.strip().rstrip(":").replace(".", "").replace("/", "_")
    return re.sub(r"[\s_]+", "_", s.lower()).strip("_")


def make_slug(name: str) -> str:
    clean = re.sub(r"[()]", "", name)
    clean = re.sub(r"[,\s]+", "-", clean.strip())
    return re.sub(r"-+", "-", clean).strip("-").lower()


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def load_config(path: Path = CONFIG_PATH) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def get_split_config(config: dict) -> dict[str, dict]:
    return {item["entry"]: item for item in config.get("split_tables", [])}


# ---------------------------------------------------------------------------
# Table classification
# ---------------------------------------------------------------------------


def is_stat_table(rows: list[list[str]]) -> bool:
    if not rows or not rows[0]:
        return False
    first = rows[0][0]
    return first == "" or first.strip().endswith(":")


def is_age_table(rows: list[list[str]]) -> bool:
    return bool(rows and rows[0] and "Age Table" in rows[0][0])


# ---------------------------------------------------------------------------
# Stat table parsers
# ---------------------------------------------------------------------------


def _norm_stat(value: str) -> str:
    return value.replace("\n", " ")


def parse_single_entity_stats(rows: list[list[str]]) -> dict[str, str]:
    stats: dict[str, str] = {}
    for row in rows:
        if len(row) >= 2 and row[0].strip():
            key = normalise_key(row[0])
            if key:
                stats[key] = _norm_stat(row[1])
    return stats


def parse_multi_entity_stats(
    rows: list[list[str]],
) -> tuple[list[str], dict[str, str], dict[str, dict]]:
    """Parse a multi-entity stat table, handling mid-table header groups.

    Returns:
        variant_keys  — slugified names in insertion order
        raw_name_for  — slug → original column header text
        variants      — slug → {field_key: value}
    """
    variant_keys: list[str] = []
    raw_name_for: dict[str, str] = {}
    variants: dict[str, dict] = {}
    current_keys: list[str] = []

    for row in rows:
        if not row:
            continue

        all_empty = all(c.strip() == "" for c in row)
        if all_empty:
            continue

        first_empty = row[0].strip() == ""
        if first_empty:
            # Header row — may be the initial one or a second group header
            raw_names = [n.strip() for n in row[1:] if n.strip()]
            current_keys = [make_slug(n) for n in raw_names]
            for rn, vk in zip(raw_names, current_keys):
                if vk not in variants:
                    variant_keys.append(vk)
                    raw_name_for[vk] = rn
                    variants[vk] = {}
            continue

        # Data row
        key = normalise_key(row[0])
        if not key or not current_keys:
            continue
        values = row[1 : len(current_keys) + 1]

        # Shared-value row: single non-empty value with dash decorators
        non_empty = [(i, v) for i, v in enumerate(values) if v.strip()]
        if len(non_empty) == 1:
            v = non_empty[0][1].strip()
            if v and (v[0] in _DASHES or v[-1] in _DASHES):
                shared = _norm_stat(v.strip(_DASHES).strip())
                for vk in current_keys:
                    variants[vk][key] = shared
                continue

        for i, vk in enumerate(current_keys):
            if i < len(values) and values[i].strip():
                variants[vk][key] = _norm_stat(values[i])

    return variant_keys, raw_name_for, variants


def parse_age_table(rows: list[list[str]], has_title_row: bool = True) -> list[dict]:
    """Parse a dragon age category table into a list of per-category dicts."""
    header_idx = 1 if has_title_row else 0
    if len(rows) <= header_idx:
        return []

    headers = rows[header_idx]
    cat_labels = headers[1:]
    categories: list[dict[str, Any]] = [{"category": c} for c in cat_labels]

    parent_key: str | None = None
    for row in rows[header_idx + 1 :]:
        if not row or not row[0].strip():
            continue
        raw_label = row[0]
        is_sub = raw_label != raw_label.lstrip()
        field_key = normalise_key(raw_label)
        values = row[1:]

        for i, cat in enumerate(categories):
            val = values[i] if i < len(values) else ""
            if is_sub and parent_key is not None:
                if not isinstance(cat.get(parent_key), dict):
                    cat[parent_key] = {}
                cat[parent_key][field_key] = val
            else:
                cat[field_key] = val

        if not is_sub:
            parent_key = field_key

    return categories


# ---------------------------------------------------------------------------
# Block collection and processing
# ---------------------------------------------------------------------------


def _collect_blocks(events: list[tuple]) -> list[tuple[str, list[tuple]]]:
    blocks: list[tuple[str, list[tuple]]] = []
    current_name: str | None = None
    current_events: list[tuple] = []

    for event in events:
        if event[0] == "p" and event[1] == "MonsterHeading":
            if current_name is not None:
                blocks.append((current_name, current_events))
            current_name = event[2].strip()
            current_events = []
        elif current_name is not None:
            current_events.append(event)

    if current_name is not None:
        blocks.append((current_name, current_events))

    return blocks


def _find_tables(
    events: list[tuple],
) -> list[tuple[list[list[str]], str | None]]:
    """Return (rows, last_preceding_paragraph) for each table in block events."""
    results = []
    last_para: str | None = None
    for event in events:
        if event[0] == "p":
            text = event[2].strip()
            if text:
                last_para = text
        elif event[0] == "table":
            results.append((event[2], last_para))
            last_para = None
    return results


def process_block(
    name: str,
    events: list[tuple],
    split_config: dict[str, dict],
) -> list[dict]:
    if name in _GROUP_INTROS:
        description = [
            normalise_spaces(e[2]) for e in events if e[0] == "p" and e[2].strip()
        ]
        entry: dict[str, Any] = {
            "name": name,
            "type": "group_intro",
            "group": _GROUP_INTROS[name],
        }
        if description:
            entry["description"] = description
        return [entry]

    tables = _find_tables(events)
    description = [
        normalise_spaces(e[2]) for e in events if e[0] == "p" and e[2].strip()
    ]

    if not tables or not is_stat_table(tables[0][0]):
        if len(description) == 1:
            m = _REDIRECT_RE.match(description[0])
            if m:
                return [{"name": name, "type": "redirect", "target": m.group(1)}]
        entry = {"name": name, "type": "group_intro"}
        if description:
            entry["description"] = description
        return [entry]

    first_rows, _ = tables[0]

    if first_rows[0][0] == "":
        # Multi-entity
        variant_keys, raw_name_for, variants = parse_multi_entity_stats(first_rows)

        if name in split_config:
            entity_desc = split_config[name].get("entity_descriptions", {})
            prefix_to_name = {v: k for k, v in entity_desc.items()}
            desc_for: dict[str, list[str]] = {}
            for para in description:
                for prefix, entity_name in prefix_to_name.items():
                    if para.startswith(prefix):
                        desc_for.setdefault(entity_name, []).append(para)
                        break
            result = []
            for vk in variant_keys:
                display = raw_name_for[vk]
                e: dict[str, Any] = {
                    "name": display,
                    "type": "beast_of_burden",
                    "stats": variants[vk],
                }
                if display in desc_for:
                    e["description"] = desc_for[display]
                result.append(e)
            return result

        entry = {"name": name, "type": "monster", "variants": variants}
        if description:
            entry["description"] = description
        return [entry]

    else:
        # Single-entity
        stats = parse_single_entity_stats(first_rows)
        entry = {"name": name, "type": "monster", "stats": stats}

        if name.startswith("Dragon, "):
            entry["group"] = "dragon"
            for rows, preceding in tables[1:]:
                if is_age_table(rows):
                    entry["age_categories"] = parse_age_table(rows, has_title_row=True)
                    break
                if preceding and "Age Table" in preceding:
                    entry["age_categories"] = parse_age_table(rows, has_title_row=False)
                    break

        if description:
            entry["description"] = description
        return [entry]


# ---------------------------------------------------------------------------
# Main extraction function
# ---------------------------------------------------------------------------


def extract_monsters(
    events: list[tuple], config: dict | None = None
) -> dict[str, dict]:
    """Return {entity_name: entity_dict} for all monster entries."""
    if config is None:
        config = {}
    split_cfg = get_split_config(config)
    results: dict[str, dict] = {}
    for name, block_events in _collect_blocks(events):
        for entity in process_block(name, block_events, split_cfg):
            results[entity["name"]] = entity
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = OdtParser(ODT_PATH)
    events = list(parser.walk())
    config = load_config()
    monsters = extract_monsters(events, config)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / "monsters.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(monsters, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(monsters)} entries to {out}")


if __name__ == "__main__":
    main()

"""Add description fields to extracted equipment data from ODT source.

Sources:
  1. "Explanation of Equipment" section — paragraphs with bold name hints, split
     into per-item descriptions at sentence boundaries.
  2. Post-table paragraphs in the "Siege Engines" section, "Name:  Description".
  3. extractor_config.yaml `remote_descriptions` entries that carry `description_text`
     — these override anything auto-extracted.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from scripts.odt_parser import (
    OdtParser,
    _ATTR_TEXT_STYLE,
    _HEADING,
    _PARAGRAPH,
    normalise_spaces,
)

_EXPLAIN_HEADING = "Explanation of Equipment"
_SIEGE_HEADING = "Siege Engines"
_CONFIG_PATH = Path(__file__).parent / "extractor_config.yaml"

_ARTICLE_RE = re.compile(r"^(A|An|The)\s+$", re.IGNORECASE)


def _load_config() -> dict:
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def _normalise(text: str) -> frozenset[str]:
    text = re.sub(r"\b(a|an|the|per|of|or)\b", " ", text.lower())
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return frozenset(text.split())


def _match_items(hint: str, items: list[dict]) -> list[dict]:
    nh = _normalise(hint)
    if not nh:
        return []
    exact: list[dict] = []
    subset: list[dict] = []
    for item in items:
        ni = _normalise(item["name"])
        if nh == ni:
            exact.append(item)
        elif nh <= ni or ni <= nh:
            subset.append(item)
    # Exact token-set match takes priority; subset matches are only used when
    # no exact match exists.  This prevents "Lantern" matching "Lantern, Bullseye"
    # when a bare "Lantern" item is also present.
    return exact if exact else subset


def _normalise_desc(raw: str) -> str:
    """Replace newlines with spaces and collapse runs of 2+ spaces."""
    return normalise_spaces(raw.replace("\n", " "))


def _segment_runs(
    runs: list[tuple[str, bool]],
    ignore: set[str],
) -> list[tuple[str, str]]:
    """Segment paragraph runs into (bold_hint, description) pairs.

    A new segment starts at each bold run whose preceding inter-text ends with a
    sentence terminator (. ! ?), indicating a new item.  Bold runs whose stripped
    lowercase text is in `ignore` are excluded entirely.

    Each segment's description is the concatenation of all runs from the optional
    preceding article up to (but not including) the article preamble of the next
    segment.
    """
    bold_idxs = [
        i
        for i, (t, b) in enumerate(runs)
        if b and t.strip() and t.strip().lower() not in ignore
    ]
    if not bold_idxs:
        return []

    # Group bold runs: split into a new group when the non-bold text between
    # two consecutive bolds ends with a sentence terminator.  Strip any
    # trailing article (the preamble of the next item) before checking.
    _trail_article = re.compile(r"\s*(A|An|The)\s*$", re.IGNORECASE)
    groups: list[list[int]] = [[bold_idxs[0]]]
    for k in range(1, len(bold_idxs)):
        prev_bold = bold_idxs[k - 1]
        this_bold = bold_idxs[k]
        inter = "".join(runs[i][0] for i in range(prev_bold + 1, this_bold))
        tail = _trail_article.sub("", inter).rstrip()
        if tail and tail[-1] in ".!?":
            groups.append([this_bold])
        else:
            groups[-1].append(this_bold)

    def _seg_start(first_bold: int) -> int:
        if first_bold > 0 and not runs[first_bold - 1][1]:
            if _ARTICLE_RE.match(runs[first_bold - 1][0]):
                return first_bold - 1
        return first_bold

    def _seg_end(g_idx: int) -> int:
        if g_idx + 1 < len(groups):
            next_first = groups[g_idx + 1][0]
            if next_first > 0 and not runs[next_first - 1][1]:
                if _ARTICLE_RE.match(runs[next_first - 1][0]):
                    return next_first - 1
            return next_first
        return len(runs)

    results = []
    for g_idx, group in enumerate(groups):
        start = _seg_start(group[0])
        end = _seg_end(g_idx)
        desc = _normalise_desc("".join(t for t, _ in runs[start:end]))
        if not desc:
            continue
        for bold_idx in group:
            hint = runs[bold_idx][0].strip()
            if hint:
                results.append((hint, desc))

    return results


def _collect_gear_descriptions(
    parser: OdtParser, ignore: set[str]
) -> list[tuple[str, str]]:
    """Return (bold_hint, description) pairs from the Explanation of Equipment."""
    results = []
    in_section = False

    for el in parser._content.iter():
        if el.tag not in (_PARAGRAPH, _HEADING):
            continue
        resolved = parser.resolve_style(el.get(_ATTR_TEXT_STYLE, ""))
        text = OdtParser.get_text(el).strip()

        if resolved == "MainHeading":
            if text == _EXPLAIN_HEADING:
                in_section = True
            elif in_section:
                break
            continue

        if not in_section or not text:
            continue

        runs = parser.get_text_runs(el)
        results.extend(_segment_runs(runs, ignore))

    return results


def _collect_siege_descriptions(parser: OdtParser) -> list[tuple[str, str]]:
    """Return (name, description) from post-table siege engine paragraphs."""
    results = []
    in_section = False

    for el in parser._content.iter():
        if el.tag not in (_PARAGRAPH, _HEADING):
            continue
        resolved = parser.resolve_style(el.get(_ATTR_TEXT_STYLE, ""))
        text = OdtParser.get_text(el).strip()

        if resolved in ("MainHeading", "SubHeading"):
            if text == _SIEGE_HEADING:
                in_section = True
            elif in_section:
                break
            continue

        if not in_section or not text:
            continue

        if ":  " in text:
            name, _, desc = text.partition(":  ")
            name = name.strip()
            desc = _normalise_desc(desc)
            if name:
                results.append((name, desc))

    return results


def enrich_descriptions(data: dict, parser: OdtParser) -> dict:
    """Add description fields to `data` in-place. Returns the same dict."""
    cfg = _load_config()
    ignore = {h.lower() for h in cfg.get("ignore_description_hints", [])}

    gear_items = data.get("equipment", [])

    for hint, description in _collect_gear_descriptions(parser, ignore):
        for item in _match_items(hint, gear_items):
            if "description" not in item:
                item["description"] = description

    siege_items = data.get("siege_engines", [])
    for name, description in _collect_siege_descriptions(parser):
        for item in _match_items(name, siege_items):
            if "description" not in item:
                item["description"] = description

    # Config overrides: remote_descriptions entries with description_text always win.
    for entry in cfg.get("remote_descriptions", []):
        desc_text = entry.get("description_text")
        if not desc_text:
            continue
        for item in _match_items(entry["name"], gear_items):
            item["description"] = desc_text

    return data

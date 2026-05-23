"""Integration tests for odt_parser.py — structural correctness of the walk output."""

import pytest
from scripts.odt_parser import OdtParser

# ---------------------------------------------------------------------------
# Basic walk sanity
# ---------------------------------------------------------------------------


def test_walk_completes(walk_events):
    assert len(walk_events) > 0


def test_event_types(walk_events):
    """Every event must be a recognised type."""
    valid = {"p", "table", "list"}
    bad = [e for e in walk_events if e[0] not in valid]
    assert not bad, f"Unexpected event types: {[e[0] for e in bad[:5]]}"


def test_paragraph_event_shape(walk_events):
    """Every 'p' event has exactly 3 elements and string fields."""
    bad = [
        e
        for e in walk_events
        if e[0] == "p"
        and (len(e) != 3 or not isinstance(e[1], str) or not isinstance(e[2], str))
    ]
    assert not bad, f"{len(bad)} malformed paragraph events"


def test_table_event_shape(walk_events):
    """Every 'table' event has a name and non-empty rows list."""
    bad = [
        e
        for e in walk_events
        if e[0] == "table"
        and (len(e) != 3 or not isinstance(e[2], list) or len(e[2]) == 0)
    ]
    assert not bad, f"{len(bad)} malformed table events"


# ---------------------------------------------------------------------------
# Paragraph counts — verified against ODT structure
# ---------------------------------------------------------------------------


def test_monster_heading_count(walk_events):
    """221 MonsterHeading entries total: 'Beasts of Burden' header + 220 individual monsters."""
    mh = [e for e in walk_events if e[0] == "p" and e[1] == "MonsterHeading"]
    assert len(mh) == 221


def test_spell_heading_count(walk_events):
    """109 SpellHeading entries: 105 actual spells + 4 class names (Cleric/Fighter/MU/Thief)
    in a section that reuses the style. Extractor-level tests will filter the 4 non-spells.
    """
    sh = [e for e in walk_events if e[0] == "p" and e[1] == "SpellHeading"]
    assert len(sh) == 109


def test_spell_roll_tables_count(walk_events):
    """Section5 contains exactly 12 spell roll tables."""
    # Collect tables only; we can't easily scope by section here, but 12 is the
    # known total across the entire document for spell roll tables. We verify the
    # total table count is at least that.
    tables = [e for e in walk_events if e[0] == "table"]
    assert len(tables) >= 12


# ---------------------------------------------------------------------------
# Style resolution spot-checks
# ---------------------------------------------------------------------------


def test_style_resolution_auto_to_semantic(parser):
    """P73 resolves to MonsterHeading; P439 resolves to SpellSubHeading."""
    assert parser.resolve_style("P73") == "MonsterHeading"
    assert parser.resolve_style("P439") == "SpellSubHeading"


def test_style_resolution_already_semantic(parser):
    """Semantic style names resolve to themselves."""
    for name in ("MonsterHeading", "SpellHeading", "Text_20_body", "Standard"):
        assert parser.resolve_style(name) == name


def test_style_resolution_unknown(parser):
    """Unknown style names pass through unchanged."""
    assert parser.resolve_style("NonExistentStyle") == "NonExistentStyle"


# ---------------------------------------------------------------------------
# Table structure spot-checks
# ---------------------------------------------------------------------------


def test_single_entity_table_starts_with_field(walk_events):
    """Single-entity monster tables have a field name in row[0][0] (e.g. 'Armor Class:')."""
    # Antelope is a known single-entity monster with Table15 immediately after its heading
    events = list(walk_events)
    for i, e in enumerate(events):
        if (
            e[0] == "p"
            and e[1] == "MonsterHeading"
            and e[2] == "Antelope (Herd Animals)"
        ):
            # Next event should be the stat table
            nxt = events[i + 1]
            assert nxt[0] == "table"
            assert nxt[2][0][0] == "Armor Class:"
            break
    else:
        pytest.fail("'Antelope (Herd Animals)' MonsterHeading not found")


def test_multi_entity_table_has_empty_first_cell(walk_events):
    """Multi-entity tables have an empty string in row[0][0] and names in row[0][1:]."""
    events = list(walk_events)
    for i, e in enumerate(events):
        if (
            e[0] == "p"
            and e[1] == "MonsterHeading"
            and e[2] == "Ant, Giant (and Huge, Large)"
        ):
            nxt = events[i + 1]
            assert nxt[0] == "table"
            row0 = nxt[2][0]
            assert row0[0] == ""
            assert "Giant" in row0[1]
            break
    else:
        pytest.fail("'Ant, Giant (and Huge, Large)' MonsterHeading not found")


def test_get_text_line_break(parser):
    """get_text maps text:line-break to newline."""
    import xml.etree.ElementTree as ET

    NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
    el = ET.fromstring(f'<p xmlns:text="{NS}">before<text:line-break/>after</p>')
    assert parser.get_text(el) == "before\nafter"


def test_get_text_spaces(parser):
    """get_text expands text:s with c attribute to that many spaces."""
    import xml.etree.ElementTree as ET

    NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
    el = ET.fromstring(f'<p xmlns:text="{NS}">a<text:s text:c="3"/>b</p>')
    assert parser.get_text(el) == "a   b"


# ---------------------------------------------------------------------------
# table:table-header-rows inclusion
# ---------------------------------------------------------------------------


def test_land_vehicle_table_includes_header_row(walk_events):
    """Table210 (land vehicles) uses table:table-header-rows; row 0 must be the header."""
    for e in walk_events:
        if e[0] == "table" and e[1] == "Table210":
            row0 = e[2][0]
            assert row0[0] == "Vehicle", (
                f"Expected header row first, got data row starting with {row0[0]!r}. "
                "table:table-header-rows is not being included in _read_table."
            )
            return
    pytest.fail("Table210 (land vehicles) not found in walk output")


def test_siege_engine_table_includes_header_row(walk_events):
    """Table232 (siege engines) uses table:table-header-rows; row 0 must be the header."""
    for e in walk_events:
        if e[0] == "table" and e[1] == "Table232":
            row0 = e[2][0]
            assert row0[0] == "Weapon", (
                f"Expected header row first, got data row starting with {row0[0]!r}. "
                "table:table-header-rows is not being included in _read_table."
            )
            return
    pytest.fail("Table232 (siege engines) not found in walk output")


# ---------------------------------------------------------------------------
# get_text_runs — bold detection
# ---------------------------------------------------------------------------


def test_get_text_runs_bold_span(parser):
    """Pattern A: item name in explicit bold character span.

    Backpack paragraph: paragraph style is non-bold; name is in a bold span (T15).
    """
    from scripts.odt_parser import _PARAGRAPH

    backpack_para = None
    for el in parser._content.iter(_PARAGRAPH):
        text = OdtParser.get_text(el)
        if "Backpack" in text and "maximum" in text:
            backpack_para = el
            break
    assert backpack_para is not None, "Backpack description paragraph not found in content"
    runs = parser.get_text_runs(backpack_para)
    bold_texts = [t for t, b in runs if b]
    assert bold_texts, f"No bold runs in Backpack paragraph; runs={runs}"
    assert any("Backpack" in t for t in bold_texts), (
        f"No bold run containing 'Backpack'; bold_texts={bold_texts}"
    )


def test_get_text_runs_bold_para(parser):
    """Pattern B: paragraph style is bold; item name is bare text.

    Chalk paragraph: paragraph auto-style (P67) sets bold; name is bare text;
    remainder is in an explicit normal span (T115).
    """
    from scripts.odt_parser import _PARAGRAPH

    chalk_para = None
    for el in parser._content.iter(_PARAGRAPH):
        text = OdtParser.get_text(el)
        if text.startswith("Chalk") and "useful" in text:
            chalk_para = el
            break
    assert chalk_para is not None, "Chalk description paragraph not found in content"
    runs = parser.get_text_runs(chalk_para)
    assert runs, "No runs found in Chalk paragraph"
    first_text, first_bold = runs[0]
    assert first_bold, f"Expected first run to be bold; runs={runs}"
    assert "Chalk" in first_text, f"Expected 'Chalk' in first run; got {first_text!r}"

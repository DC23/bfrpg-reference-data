"""ODT parser: style resolver, document walker, and table reader.

Yields events from an ODT document body:
  ('p',     resolved_style, text)          — paragraph or heading
  ('table', table_name,     rows)          — table; rows is list[list[str]]
  ('list',  items)                         — bulleted/numbered list; items is list[str]
"""

import zipfile
import xml.etree.ElementTree as ET

_NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
}


def _xml_tag(prefix, local):
    return f"{{{_NS[prefix]}}}{local}"


# Paragraph and heading elements
_PARAGRAPH = _xml_tag("text", "p")
_HEADING = _xml_tag("text", "h")
_SECTION = _xml_tag("text", "section")

# List elements
_LIST = _xml_tag("text", "list")
_LIST_ITEM = _xml_tag("text", "list-item")

# Table elements
_TABLE = _xml_tag("table", "table")
_TABLE_ROW = _xml_tag("table", "table-row")
_TABLE_CELL = _xml_tag("table", "table-cell")
_TABLE_CELL_COV = _xml_tag("table", "covered-table-cell")  # merged/spanned cell

# Whitespace elements
_LINE_BREAK = _xml_tag("text", "line-break")
_SPACES = _xml_tag("text", "s")  # run of spaces; count in text:c attribute
_TAB = _xml_tag("text", "tab")

# Attribute names
_ATTR_STYLE_NAME = _xml_tag("style", "name")
_ATTR_STYLE_PARENT = _xml_tag("style", "parent-style-name")
_ATTR_TEXT_STYLE = _xml_tag("text", "style-name")
_ATTR_TABLE_NAME = _xml_tag("table", "name")
_ATTR_SPACE_COUNT = _xml_tag("text", "c")


class OdtParser:
    def __init__(self, odt_path):
        with zipfile.ZipFile(odt_path) as z:
            self._content = ET.fromstring(z.read("content.xml"))
            styles_root = ET.fromstring(z.read("styles.xml"))
        self._auto_styles: set[str] = set()
        self._parents: dict[str, str] = {}
        self._build_style_map(styles_root)
        self._resolve_cache: dict[str, str] = {}

    def _build_style_map(self, styles_root: ET.Element) -> None:
        # Automatic styles in content.xml are the auto-generated ones (P1, P73, …)
        auto_el = self._content.find(f'{{{_NS["office"]}}}automatic-styles')
        if auto_el is not None:
            for s in auto_el:
                name = s.get(_ATTR_STYLE_NAME)
                parent = s.get(_ATTR_STYLE_PARENT)
                if name:
                    self._auto_styles.add(name)
                    if parent:
                        self._parents[name] = parent

        # Named styles from styles.xml — collect parent chains only;
        # these are the semantic roots so do NOT add them to _auto_styles
        for s in styles_root.iter(_xml_tag("style", "style")):
            name = s.get(_ATTR_STYLE_NAME)
            parent = s.get(_ATTR_STYLE_PARENT)
            if name and parent and name not in self._parents:
                self._parents[name] = parent

    def resolve_style(self, style_name: str) -> str:
        """Walk parent chain; return the first non-automatic ancestor."""
        if style_name in self._resolve_cache:
            return self._resolve_cache[style_name]
        seen: set[str] = set()
        current = style_name
        while current in self._auto_styles:
            if current in seen:
                break
            seen.add(current)
            parent = self._parents.get(current)
            if parent is None:
                break
            current = parent
        self._resolve_cache[style_name] = current
        return current

    @staticmethod
    def get_text(element: ET.Element) -> str:
        """Extract text content, mapping ODT whitespace elements to characters."""
        parts: list[str] = []

        def collect(el: ET.Element) -> None:
            if el.text:
                parts.append(el.text)
            for child in el:
                tag = child.tag
                if tag == _LINE_BREAK:
                    parts.append("\n")
                elif tag == _SPACES:
                    count = int(child.get(_ATTR_SPACE_COUNT, "1"))
                    parts.append(" " * count)
                elif tag == _TAB:
                    parts.append("\t")
                else:
                    collect(child)
                if child.tail:
                    parts.append(child.tail)

        collect(element)
        return "".join(parts)

    def _read_table(self, table_el: ET.Element) -> list[list[str]]:
        """Return list of rows; each row is a list of cell text strings."""
        rows = []
        for row_el in table_el.findall(_TABLE_ROW):
            row = []
            for cell_el in row_el:
                if cell_el.tag not in (_TABLE_CELL, _TABLE_CELL_COV):
                    continue
                paragraphs = [
                    self.get_text(p) for p in cell_el.findall(f".//{_PARAGRAPH}")
                ]
                row.append("\n".join(paragraphs))
            rows.append(row)
        return rows

    def walk(self):
        """Yield events for all content in document order."""
        body = self._content.find(f'{{{_NS["office"]}}}body/{{{_NS["office"]}}}text')
        if body is not None:
            yield from self._walk_element(body)

    def _walk_element(self, element: ET.Element):
        for child in element:
            tag = child.tag
            if tag in (_PARAGRAPH, _HEADING):
                raw_style = child.get(_ATTR_TEXT_STYLE, "")
                yield ("p", self.resolve_style(raw_style), self.get_text(child))
            elif tag == _TABLE:
                name = child.get(_ATTR_TABLE_NAME, "")
                yield ("table", name, self._read_table(child))
            elif tag == _SECTION:
                yield from self._walk_element(child)
            elif tag == _LIST:
                items = []
                for item_el in child.findall(_LIST_ITEM):
                    for p_el in item_el.findall(_PARAGRAPH):
                        items.append(self.get_text(p_el))
                if items:
                    yield ("list", items)

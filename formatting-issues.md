# BFRPG ODT Formatting Issues

Structural inconsistencies found in the source ODT during automated extraction development. These may be invisible to readers but detectable by the extractor. Intended for reporting to the BFRPG project.

All issues refer to `Basic-Fantasy-RPG-Rules-r142.odt` (4th Edition, Release 142, February 22, 2025).

---

## Bestiary

- **Swamp Dragon age table heading** (p. ~85): The "Swamp Dragon Age Table" title appears as a standalone paragraph immediately before the table, rather than embedded as the first row of the table itself. All other dragon age tables carry their title in row 0 of the table. Consistent placement is easier to parse.

# BFRPG ODT Formatting Issues

Structural inconsistencies found while building the extractor. They're invisible to readers but detectable by tooling, and are logged here for reporting upstream to the BFRPG project.

All issues are in `Basic-Fantasy-RPG-Rules-r142.odt` (4th Edition, Release 142, February 22, 2025).

---

## Bestiary

- **Swamp Dragon age table heading** (p. ~85): The "Swamp Dragon Age Table" title is a standalone paragraph immediately before the table rather than embedded as row 0. Every other dragon age table puts the title in row 0; the Swamp Dragon is the only exception.

## Spells

- **Range/Duration split** (multiple spells): Around 8 spells split Range and Duration across two paragraphs. The primary header has class/level and Range; a following SpellSubHeading paragraph carries the Duration alone (e.g. `"Duration:instantaneous"`). Affected spells include Cure Serious Wounds, Fly, and several shared Cleric/Magic-User spells. The rest put both on one line.

# BFRPG ODT formatting issues

Structural quirks found while building the extractor. The rendered output looks fine in both cases; the difference only shows up in the raw XML.  Logged for upstream reporting to the BFRPG project.

All issues are in `Basic-Fantasy-RPG-Rules-r142.odt` (4th Edition, Release 142, February 22, 2025).

---

## Bestiary

- **Swamp Dragon age table heading** (p. ~85): Every other dragon age table embeds its title in row 0. The Swamp Dragon's "Swamp Dragon Age Table" heading is a standalone paragraph immediately before the table instead.

## Spells

- **Split SpellHeading format** (8 spells): The standard layout is two paragraphs — SpellHeading (`name\tRange:\tvalue`) then SpellSubHeading (`class level\tDuration:\tvalue`). Eight spells have names long enough that Range is pushed to a new line, which in the ODT becomes a third paragraph: SpellHeading (name only) → SpellMidHeading (`class level\tRange:\tvalue`) → SpellSubHeading (`\tDuration:\tvalue`, empty class part). Affected: Cure Serious Wounds, Hallucinatory Terrain, Invisibility 10' Radius, Protection from Evil, Protection from Evil 10' Radius, Protection from Normal Missiles, Purify Food and Water, Speak with Monsters.

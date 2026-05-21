# Basic Fantasy Role-Playing Game Reference Data Project Proof of Concept

A proof of concept project to create a human and machine readable reference data set of [Basic Fantasy Role-Playing Game](https://www.basicfantasy.org/) (BFRPG) data that can be used by multiple people, for multiple projects and purposes, without all of us needing to reinvent and recreate the processes of extracting, cleaning and updating the information from the core rules.

I'm inspired by the realisation that multiple projects exist with this information in multiple formats already - JSON, RST, HTML and who knows what else. But they all seem to lag behind when there are updates. For myself, I'd like to help move the [Basic Fantasy RPG Core Rules](https://foundryvtt.com/packages/basicfantasyrpg-corerules-en) content module for the Foundry VTT along to the current edition of the BFRPG rules as well as the current edition of Foundry. But doing so looks like it would require hand-editing a huge number of large Foundry-specific JSON data files. It's a lot of work, and once done, only that one project would benefit.

Why not do just a little more work, and make the essential BFRPG information available in a use-neutral way that could be shared? That's the idea behind this project.

By using the XML data structures and named styles ("MonsterHeading", "SpellHeading", "SpellSubHeading" etc), the parser walks the input ODT file, generating a stream of typed events. The token stream is consumed by data extractors - monsters, weapons, spells, vehicles, etc - which construct the output data structures into json.

From json, the world is our oyster for downstream use. Text, yaml, rst, Python dictionaries, or whatever you need. Consumers of the reference data are then free to massage it as required. Derive new fields, reclassify, add things, recombine or restructure as you like. I know that's something I'll need to do for my end use in Foundry. There's all sorts of baggage that Foundry requires that needs to be added, but that's something that happens after the data is consumed from this project.

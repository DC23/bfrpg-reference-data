# Basic Fantasy Role-Playing Game Reference Data Project Proof of Concept

A proof of concept project to create a human and machine readable reference data set
of Basic Fantasy Role-Playing Game (BFRPG) data that can be used by multiple people, for
multiple projects and purposes, without all of us needing to reinvent and recreate the
processes of extracting, cleaning and updating the information from the core rules.

I'm inspired by the realisation that multiple projects exist with this information in multiple
formats already - JSON, RST, HTLM and who knows what else. But they all seem to lag behind when there are updates. For myself, I'd like to help move the [Basic Fantasy RPG Core Rules](https://foundryvtt.com/packages/basicfantasyrpg-corerules-en) content module for the Foundry VTT along to the current edition of the BFPRG rules as well as the current edition of Foundry. But doing so looks like it would require hand-editing a huge number of large Foundry-specific JSON data files.

It's a lot of work, and once done, only that one project would benefit.

Why not do just a little more work, and make the essential BFRPG information available in a use-neutral way that could be shared? That's the idea behind this project.

Starting with the bestiary, but not stopping with that, information will be extracted in plain text into files, one per item. Those alone will be useful. Then a Python processing pipeline will process those human readable files into JSON, and possibly other formats that will represent that data in an easily digestible format for any programatic use. At this stage, it's still just the information as contained in the BFRPG rules, no additions and no modifications for specific purposes.

Consumers of the reference data are then free to massage it as required. Derive new fields, reclassify, add things, recombine or restructure as you like. I know that's something I'lld need to do for my end use in Foundry. There's all sorts of baggage that Foundry requires that needs to be added, but that's something that happens after the data is consumed from this project.

---
name: foundry-adventure-prep
description: Prep a published adventure module (DMsGuild/AL PDF, any line: PS-DC-PUB, FR-DC, CCC, DDAL…) for running in Foundry VTT. Builds the adventure folder under D:\FoundryVTT\Data\img\adventures (PDF copy, !Cover.webp, maps as original + .webp with grid measured) and writes a "Prep Doc.md" (overview, maps, monsters and modifications, scaling, rolltables, handouts, rewards, gold), all transcribed verbatim for pasting into Foundry. Use when Dan hands over a module PDF or maps zip and says "prep today's adventure", "prep this for Foundry", "get this ready for the VTT", or names an adventure code he's about to run, even without saying "skill".
---

# Foundry adventure prep

Dan runs AL one-shots in Foundry VTT, usually at the **Wednesday 7pm PandoDnD** drop-in game and often prepped the same day. "Prepping an adventure" means turning a DMsGuild download into the on-disk folder Foundry reads from, plus a `Prep Doc.md` he copies from while building the adventure in Foundry.

This is **mechanical extraction, not creative planning.** Don't ask about story, framing, series arcs, or AL tier and levels: characters are portable, and drop-in players bring whatever fits. Transcribe the module; don't redesign it. Flag oddities to Dan rather than fixing them.

## Where things live

| Thing | Path | Notes |
|---|---|---|
| Foundry data root | `D:\FoundryVTT` | Authoritative: `dataPath` in `D:\FoundryVTT\Config\options.json`. Contains `Data\`, `Backups\`, `Logs\` |
| **Adventure asset folders** | `D:\FoundryVTT\Data\img\adventures\<CODE> <Title>\` | One per adventure, flat (no subfolders). Siblings show the naming convention across every line |
| Local working worlds | `D:\FoundryVTT\Data\worlds\` | Dan builds scenes, actors, and journals here by hand |
| Downloads (PDFs, map zips) | `D:\Downloads\` | DMsGuild files carry a numeric prefix (`1533714-`, `2571479-`) that is a download/vendor id, **not** the product id |
| **Finished bundles** | `D:\Downloads\Foundry Transfer\` | Adventure Bundler exports, one `.zip` per completed adventure. A zip here means the adventure is done, past prep |
| Adventure catalog (rich) | `C:\Users\decha\dev\al_adventure_catalog\maintaindb\_dc\*.json` | `code`, `title`, `authors`, `level_range`, `apl`, `tiers`, `season`, `hours`, `url` (affiliate link already included) |
| Adventure catalog (flat) | `C:\Users\decha\dev\al_adventure_catalog\assets\data\catalog.json` | `{adventures:[{c: code, n: title, i: product id, a: authors, …}]}`; URL = `https://www.dmsguild.com/product/{i}/?affiliate_id=171040` |
| Stale docs | `C:\Users\decha\AppData\Local\FoundryVTT\PREP-NOTES.md` | An older write-up. Its transfer path `D:\downloads\FoundryTransfer\` is wrong (the real folder has a space) |
| Scripts | `<this skill dir>\scripts\` | Run via `uv run --with …` (never bare `python`) |

**Two stages, don't conflate them:** *prepped* means the folder above exists with its Prep Doc. *Finished* means Dan built it in Foundry and exported a bundle to `Foundry Transfer`. Before starting, check both places: an existing folder means update it rather than rewrite, and an existing bundle means it's already been run.

## Step 1: Identify the module and its files

- Find the PDF and companions in `D:\Downloads`: glob by code or title fragments. Expect some mix of:
  - the adventure PDF, sometimes `(FULL_VERSION)` alongside a `(DM_Guide_Maps_Print-Friendly)` PDF
  - map zip(s), e.g. `…PS-DC-PUB-13_to_16_Maps_etc.zip` covering several adventures, or `…MAPS_A-D.zip` **plus** a `…(DM_Copy).zip`
  - loose map JPGs/PNGs, VTT token assets (e.g. `…(Token_Asset_for_VTT_25x25).png`), and regional handout maps
- Catalog lookup for the header line: grep `maintaindb\_dc` for the code **or the title** (codes drift: the catalog has `FR-DC-LOOSE-01` where the PDF says `-001`), then read the record with `jq`. Fall back to `catalog.json`. **The PDF's printed code wins** for the folder name; note any catalog mismatch.
- Folder name: `<CODE> <Title>`, both as printed in the module (e.g. `PS-DC-PUB-15 Spider Hunt`, `FR-DC-GAMEJAM-01 Only (Peacock) Fans`).

## Step 2: Build the folder

```
uv run --with pymupdf --with pillow python "<skill>\scripts\prep_adventure.py" --pdf "<pdf>" [--name "<CODE> <Title>"] [--zip "<zip>" ...] [--zip-match "<regex>"] [--maps "<img>" ...] [--cover pdf|<image>|none] [--dry-run]
```

- It copies the PDF (never moves it), extracts or copies maps flat, writes a `.webp` beside each original (quality 80, about 4× smaller), and renders `!Cover.webp`. It's idempotent.
- PS-DC-PUB filenames parse automatically, and the multi-adventure zip is filtered to that number. **Every other line needs `--name`.**
- **Pass the clean/player map zip, not the `(DM_Copy)` one.** DM copies have area labels and "ADD VTT TOKEN" notes burned into the art. Use them only as a reference (e.g. to confirm a rotation).
- Include token assets and regional or handout maps via `--maps`.
- **No map download at all?** As a last resort, rip maps from the PDF:
  `uv run --with pymupdf --with pillow --with numpy python "<skill>\scripts\pdf_assets.py" images "<pdf>" "%TEMP%\<code>-imgs"`
  Look at the candidates, then feed the keepers in via `--maps`, renamed to display names (`Luskan Market.png`).
- **GM markers printed on a PDF map** (spawn letters, "Party Start" boxes): make a player copy with the markers painted over and the grid redrawn in the sampled line colour and width (Pillow). Keep the marked one as `<Name> (GM).webp`, and record marker positions as grid squares in the Prep Doc for token placement.
- **Map transforms the text asks for:** read the adventure's map notes. It may call for a rotation to match the printed appendix, or a doubled grid ("34 × 44"), which is a Foundry grid-density setting, not a resize. For tall portrait battle maps, offer a landscape `(Rotated)` variant, since landscape reads better on a monitor.
- **Cover:** always **Read `!Cover.webp` to confirm it's really the cover.** Sources, in order: the PDF front page (the default, usually right), then the DMsGuild product page, then ask Dan. **Never scrape DMsGuild.** Open the product page in the browser, have Dan save the image, then rerun with `--cover "<that image>"`.
- **Verify, don't trust:** list the folder with sizes and webp dimensions (the script prints this).

## Step 3: Grids (a toolbox; Dan finishes by eye)

```
uv run --with pymupdf --with pillow --with numpy python "<skill>\scripts\pdf_assets.py" grid --preview "%TEMP%\grid" "<map.webp>" ...
```

- It measures **X and Y independently** (rectangular grids exist) and reports px/square, offset, square count, and signal strength. `--preview` writes an overlay PNG; **look at it** before reporting.
- The only numbers Foundry needs are **Grid Size (px)** and the **Offset (H/V px)**. Everything else is constant: Square, 5 ft, padding 0.25.
- **Grid scale is per map pack, not per adventure.** Never extrapolate a confirmed value from one map to another in the same zip. In GAMEJAM-01 the Docks were 140 px at 1:1, but the `TC_ItW Forest` maps needed **70 px with the image scaled to 0.971** (they measure about 71.6).
- The PS-DC-PUB series is about **70 px/5 ft**, even when the image isn't an exact multiple (Spider Hunt is 1118 × 1538).
- For weak signal (painted or gridless maps), use the filename or credits (`16x22`, `22x17`, `72 DPI`) or a square count from the text. Overview and town maps with scale bars (200 ft) aren't gridded: say so.
- Report values as **measured, not confirmed**. Write "confirmed" only after Dan has lined the grid up in Foundry (its ruler tool: SHIFT+wheel scales the image, ALT+wheel changes grid size, arrow keys shift the offset).

## Step 4: Read the module (layout analysis before vision)

- Text: `pdf_assets.py text "<pdf>" "%TEMP%\<code>.txt"`, then read it fully. Use PyMuPDF, not pypdf, which breaks DMsGuild PDFs into one word per line.
- Layout manifest: `uv run --with pymupdf python "<skill>\scripts\analyze_layout.py" "<pdf>"` (`--json` is also available). It finds shaded sidebars (labelled `npc`, `callout`, `modifier`, or `boilerplate`, with body text and the nearest heading), lists which pages actually need vision (cover, map, modifier boxes beside stat blocks), cross-checks creatures named in "Adjusting the Scene" against stat blocks, and flags player-handout appendices and "Roll a dX" tables.
  - **It's tuned to the PS-DC-PUB template and fails safe elsewhere.** "0 boxes" on an unfamiliar template means the template wasn't scanned, not that nothing is there. GAMEJAM-01's coral `<Creature> (<Flavor>) MODIFICATIONS` boxes, one per stat block in a Creature Statistics appendix, were missed entirely at first. On a new template, page through the stat-block appendix by vision.
  - Treat each QA "missing stat block" flag as something to **verify**: it may be a reflavoured block, a plain Monster Manual lookup, or a genuine omission to prep.
- Vision-read only the pages that need it: render with PyMuPDF (`page.get_pixmap(dpi=…)`) and Read the PNG. The cover is usually a flattened image with no text layer, so transcribe the Overview from the rendered cover.
- A sidebar is often **repeated beside each affected stat block with different scope wording**. Take the union (Spider Hunt: "drow and driders" on one page, "the drow" on the next, so all three drow blocks). Ask Dan only when the instances genuinely conflict. If you can't attribute a sidebar, include it near the monster list anyway.

## Step 5: Write `Prep Doc.md`

### Verbatim rule: fix the presentation, never the words
Reproduce game text exactly. **Don't** reword, paraphrase, drop or add words, "fix" typos, or change inline capitalization. Spider Hunt's "When spell is copied in this way", "monsterous", and "Optimised" all stay as printed. The only allowed changes:
- ALL-CAPS titles become Title Case headings
- hard-wrapped lines are rejoined into paragraphs (keeping real paragraph breaks)
- the type/rarity line goes in italics, keeping its printed capitalization
- named minor-property labels are bolded (`**Harmonious.**`)
- a pure-flavor paragraph may optionally be italicized

If something looks wrong, leave it and flag it (Errata section, or tell Dan). Dan pastes this text straight into Foundry, so it must match the book.

**Leave out read-aloud boxed text and scene-by-scene walkthroughs**, since Dan runs those from the PDF.

### Sections, in order (include only what the module has)

```markdown
# <CODE>: <Title> — Prep Doc

<CODE> · <Setting (City/Plane)> · Tier N · APL N · by <Author> · [DM's Guild](<catalog url>)

## Overview
Front-page text verbatim: title lines, blurb, the "A Two-Hour Adventure for…" line, **Content Warning:**.
(These seed the Bundler export: the blurb becomes the adventure description and the "A Two-Hour…" line the caption.)
**Structure:** one bullet per part (what happens, what's a fight or puzzle, story objectives). Series or sequel notes if relevant.

## Maps
In this folder: `<full folder path>`
| Map | Type | Foundry file | Pixels | Grid | Original |     <- Original LAST: long source filenames blow out the column width
Italic note: which grid values are measured and which confirmed; covers vs battle maps vs overview maps; rotations and doubled grids; token assets; GM-marker token placement.

## Monsters
- <Creature> (<NPC name / flavor>) — CR N          (the module's stat-block names)
Mark sidebar-modified creatures with a trailing ` \*`, then a blockquote per sidebar with the modification text.
### <Creature> Modifications              (verbatim, when the module has a Creature Statistics appendix of them)
### Adjusting the Scene — by Party Strength   (strength table plus per-encounter bullets, verbatim)
### Stat blocks (importer text)           (ONLY for creatures Dan can't drag from the DDB Monsters compendium:
                                          module-custom blocks. Plain text in ```text blocks, standard 5e layout;
                                          fill in missing average damage such as "6 (1d6 + 3)" and say so)

## Rolltable: <Name> (dX, <when>)        (verbatim table; note that it *could* be a Foundry Rolltable, but don't build one unless asked)
## Group Checks / Puzzles               (outcome tables and puzzle answers Dan needs at hand, verbatim)

## Handout: <Appendix Title>           (ASK Dan before making each one. Pure text/table: transcribe as Markdown, blanking
                                        player-fill columns. Render to `Handout - <Title>.webp` only when the layout carries meaning)

## Rewards
### Advancement
### Reward: <Item Name>                (heading matches the Foundry journal-page name)
*Type, Rarity (Attunement)*  then the full text verbatim: mechanics, minor properties, flavor, "This item is found in…"

## Gold
The "If found during the adventure the following items are converted to gold…" intro, verbatim if present.
| Item | Gold Value |  ending in **Maximum**, then an italic sanity check that the items sum to it.
Odd rows are usually legitimate (Spider Hunt's "Reward — 500 gp" is an NPC bounty): keep them, and at most mention them.

## Errata                              (truncated tables, missing abilities, inconsistencies)
```

AL reward convention: magic items go on **every** player's available list rather than to one owner. Don't write "unlock".

## Step 6: Hand off

Link `Prep Doc.md` in the report, and summarize:
- the folder contents (verified)
- grid values per scene (measured or confirmed), with preview paths
- the cover check result
- creatures needing custom stat blocks
- handout and rolltable candidates, **as questions**
- errata

**What Dan does in Foundry (don't do it for him, but know it so the Prep Doc serves it).** He works in a **local** working world, because the DDB Monsters compendium is local-only and Bundler doesn't embed assets from Forge-hosted worlds.
- **Scenes:** a `!Cover` scene set active (the player landing screen), plus the battle-map scenes. Walls and vision only for complex maps; simple ones stay fully visible.
- **Actors:** dragged from the DDB Monsters compendium into an adventure folder, tweaked per the modifications, with Tokenizer tokens.
- **Journals:** a GM journal named after the adventure (with `Reward: <item>` pages), plus an **empty-by-design** `<Adventure> (player)` journal (Observer for everyone). He drags entries into the player journal during play, so an empty player journal isn't a gap.
- **Pasting:** Foundry's default journal editor strips Markdown `*`/`**` on paste; he re-applies them or sets the page format to Markdown.
- **Export:** Adventure Bundler (v0.2.5) to `D:\Downloads\Foundry Transfer\<CODE> <Title>.zip`, then import on the server.

Nothing here is a git repo, so don't commit. After the session, `/scrollcase-prep` handles the transcript.

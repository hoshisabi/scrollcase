---
name: scrollcase-wiki-add
description: >-
  Add a new wiki page to a scrollcase campaign — NPC, item, location, lore, or character.
  Gathers details, drafts the page, reviews the image prompt, generates the image, then commits
  and pushes.
---

Add a new wiki page to a scrollcase campaign — NPC, item, location, lore, or character. Gathers details, drafts the page, reviews the image prompt, generates the image, then commits and pushes.

`$ARGUMENTS` may contain a campaign name (`pandodnd`, `icewind-dale`, `log`) and/or a page type (`npc`, `item`, `location`, `lore`, `character`). Omit either or both to be asked.

## Paths

| Campaign | Campaign dir | DM dir |
|---|---|---|
| pandodnd | `C:\Users\decha\dev\hoshisabi.github.io\rpg\pandodnd` | `C:\Users\decha\dev\hoshisabi-dm\pandodnd` |
| icewind-dale | `C:\Users\decha\dev\hoshisabi.github.io\rpg\icewind-dale` | `C:\Users\decha\dev\hoshisabi-dm\icewind-dale` |
| log | `C:\Users\decha\dev\hoshisabi.github.io\rpg\log` | `C:\Users\decha\dev\hoshisabi-dm\log` |

| Thing | Path |
|---|---|
| scrollcase scripts | `C:\Users\decha\dev\scrollcase` |

## Page types — layout, directory, and fields

| Type | layout | Public dir | Extra frontmatter |
|---|---|---|---|
| NPC | `npc` | `public/npcs/` | `role`, `race`, `status` |
| Item | `location` | `public/items/` | — |
| Location | `location` | `public/locations/` | `also_known_as` (list, optional) |
| Lore | `lore` | `public/lore/` | `category` |
| Character | `character` | `public/characters/` | `player`, `player_slug`, `class`, `dnd_beyond` (optional) |
| Player | `player` | `public/players/` | `player_slug` (same as filename; lists characters via layout) |

NPC `status` conventions: `Active`, `Active — first appeared Session N`, `Departed`, `Missing — presumed dead, Session N`.

## Image prompt tag system

The campaign applies a base style prefix automatically. Tags in the prompt select a context overlay:

| Tag | When to use |
|---|---|
| *(no tag)* | NPC portraits, outdoor locations — arctic exterior context added automatically |
| `[interior]` | Indoor scenes: shelters, chambers, ruins interiors — replaces arctic exterior with warm stone interior |
| `[treasure]` | Item close-ups — tight shot on a magical object, no character |

Write the tag at the start of the prompt string, e.g. `"[interior] a dusty stone passage..."`.

Do **not** put "arctic" or "snow" language into an `[interior]` prompt — the tag handles setting context.
For NPC race: never use D&D race names (tabaxi, gnome when it would be ambiguous, etc.). Describe physical traits — e.g. `"a small slight woman with sharp watchful eyes"` rather than `"a gnome wizard"`.

## Step 1 — Campaign and page type

If not given in `$ARGUMENTS`, ask using AskUserQuestion (combine into one call if both are unknown):

- **Campaign**: pandodnd / icewind-dale / log
- **Page type**: NPC / Item / Location / Lore / Character / Player

## Step 2 — Research from DM notes

Before asking the user for details, search the DM directory for existing information about the subject. Do these in parallel with reading 2–3 existing public pages of the same type (to calibrate tone) and `campaign.yaml`:

1. **Grep `<dm-dir>/threads.md`** for the subject's name — this often has role, status, and plot context.
2. **Read the most recent session file** in `<dm-dir>/sessions/` — check for the subject's first or most prominent appearance.
3. **Grep all session files** in `<dm-dir>/sessions/` for the subject's name to catch earlier appearances.

Draft the page using what you found. Ask the user only for anything critical that's still missing — e.g. status confirmation, or context that wasn't in the DM notes. Don't ask for things you can infer. Don't include DM-only information (marked `[DM ONLY]`) on the public page.

If the user provided information in their initial message, incorporate it alongside what you found.

## Step 3 — Draft the page

### Slug and filename

Slugify the title: lowercase, spaces → hyphens, drop punctuation. E.g. `"Thessaly Vorn"` → `thessaly-vorn`. Write to `<public-dir>/<slug>.md`.

### Frontmatter

```yaml
---
campaign_url: /rpg/<campaign-slug>/public/
campaign_name: <campaign.yaml name>
layout: <layout>
title: <Title>
# NPC only:
role: <short role description>
race: <physical description, not D&D race name>
status: <status string>
# Location only (if applicable):
also_known_as:
  - <alias>
# Lore only:
category: <category>
# Character only:
player: <Player Name>
player_slug: <registry slug from dm/player-registry.yaml — required; ask if ambiguous>
class: <Race Class Level>
dnd_beyond: <URL — omit if unknown>
# Player only:
player_slug: <same as filename slug>
# All types:
image: /rpg/<campaign-slug>/public/<type-dir>/images/<slug>.png
image_prompt: "<prompt — see Step 4>"
---
```

When creating a **character** page, resolve `player_slug` from `<dm-dir>/player-registry.yaml` (exact `display_name` or `slug` match). If nothing matches cleanly, or an existing `player_slug` on the page disagrees with the registry, ask the user — do not guess. Also ensure `public/players/<player_slug>.md` exists (create a stub with `layout: player` if missing); the player layout auto-lists characters by `player_slug`.
### Body

Write in the established voice of the campaign's existing pages — not summary bullet points, not a stat block. Prose paragraphs. For NPCs: who they are, how they relate to the party, what the reader should know. For items: where it was found, what it does, any story weight. For locations: what it is, what it looks like, what happened here. For lore: what this tradition/concept/fact means in the world.

Use `## Sections` to break up longer pages, matching the conventions of existing pages of that type.

Do **not** include DM-only information (future plot hooks, secrets the party hasn't learned). This is the public wiki.

### Image prompt

Draft an image prompt following the style of existing pages of the same type. Apply the correct tag (`[interior]`, `[treasure]`, or none). The campaign style prefix is applied automatically — do not repeat it in the prompt.

## Step 4 — Image prompt review

Show the user the draft image prompt clearly:

```
Proposed image prompt:

  "<the prompt>"

Campaign will prepend its base style automatically.
```

Then use AskUserQuestion:

- question: "How does the image prompt look?"
- header: "Image prompt"
- options:
  - "Looks good — generate it" (Recommended)
  - "Edit it first" — ask in chat what to change, update the frontmatter in the draft, re-show the revised prompt and ask again

Once accepted, write the file to disk before generating (the script reads from the file).

## Step 5 — Generate the image

```powershell
cd C:\Users\decha\dev\scrollcase
uv run python generate_artwork.py `
  --campaign-dir "<campaign-dir>" `
  "<campaign-dir>\<public-dir>\<slug>.md"
```

Note: always use `--campaign-dir` with the explicit path — do not rely on `.env` CAMPAIGN_DIR.

After generation, display the image with the Read tool so the user can see it.

Then use AskUserQuestion:

- question: "How does the image look?"
- header: "Image"
- options:
  - "Looks good" (Recommended)
  - "Regenerate with the same prompt" — run with `--force`
  - "Edit the prompt and regenerate" — ask in chat what to change, update the frontmatter, re-show the prompt, then run with `--force`

Repeat regeneration until the user accepts.

## Step 6 — Confirm and push

Show a summary of what will be committed:

```
Ready to commit:
  <campaign-dir>/public/<type-dir>/<slug>.md     (new)
  <campaign-dir>/public/<type-dir>/images/<slug>.png   (new)
```

Use AskUserQuestion:

- question: "Commit and push?"
- header: "Push"
- options:
  - "Yes — commit and push" (Recommended)
  - "Not yet — I want to make more changes"

If confirmed:

```powershell
cd C:\Users\decha\dev\hoshisabi.github.io
git add rpg/<campaign-slug>/public/<type-dir>/<slug>.md `
        rpg/<campaign-slug>/public/<type-dir>/images/<slug>.png
git commit -m "feat(<campaign-slug>): add <type> page — <Title>"
git push
```

Report success with the committed filenames.

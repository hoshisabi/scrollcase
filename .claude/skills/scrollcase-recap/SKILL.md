---
name: scrollcase-recap
description: >-
  Generate the player-facing session recap page for a scrollcase campaign. Reads the context
  file and transcript produced by `/scrollcase-prep`, drafts the session page, shows it to the
  user for review and correction, then writes it.
---

Generate the player-facing session recap page for a scrollcase campaign. Reads the context file and transcript produced by `/scrollcase-prep`, drafts the session page, shows it to the user for review and correction, then writes it.

`$ARGUMENTS` may contain a campaign name (`pandodnd`, `icewind-dale`, `log`) and/or a date (`YYYY-MM-DD`). If either is omitted, Step 1 asks for it — with a fallback to auto-detecting the most recent context file that has no published page.

## Paths

| Thing | Path |
|---|---|
| pandodnd campaign dir | `C:\Users\decha\dev\hoshisabi.github.io\rpg\pandodnd` |
| icewind-dale campaign dir | `C:\Users\decha\dev\hoshisabi.github.io\rpg\icewind-dale` |
| log campaign dir | `C:\Users\decha\dev\hoshisabi.github.io\rpg\log` |
| pandodnd DM dir | `C:\Users\decha\dev\hoshisabi-dm\pandodnd` |
| icewind-dale DM dir | `C:\Users\decha\dev\hoshisabi-dm\icewind-dale` |
| log DM dir | `C:\Users\decha\dev\hoshisabi-dm\log` |

## Step 1 — Find the context file

Resolve the **campaign** and **date**, asking for whatever `$ARGUMENTS` didn't supply:
- **Campaign** — if named in `$ARGUMENTS`, use it; otherwise AskUserQuestion, header **Campaign**, options: `pandodnd`, `icewind-dale`, `log` (AskUserQuestion adds *Other* automatically).
- **Date** — if given in `$ARGUMENTS`, use it; otherwise AskUserQuestion, header **Date**, options: **Today** (the current date), **Yesterday** (current date − 1 day), **Enter a date** (`YYYY-MM-DD`). Resolve Today/Yesterday to a concrete `YYYY-MM-DD` using the current system date.

Then load `<dm-dir>/sessions/<date>-context.md` for the chosen campaign. If no context file exists for that campaign/date, say so and fall back to the most recent context file that has **no** corresponding `public/sessions/YYYY-MM-DD.md` (offer it before proceeding).

## Step 2 — Read all the inputs

Read these in parallel:

- The context file (`<dm-dir>/sessions/YYYY-MM-DD-context.md`) — date, adventure code/title, roster, transcript path
- The full transcript at the path listed in the context file
- `campaign.yaml` — `name`, `dm`, `default_portrait`
- All `public/characters/*.md` files — collect the `image:` field from each character's frontmatter, keyed by character name and slug
- All existing `public/sessions/*.md` files — count them to determine the session number for the new page's `title`

## Step 3 — Draft the session page

Produce a complete session page matching the established format exactly. Study `public/sessions/2026-05-13.md` and `public/sessions/2026-05-20.md` as canonical references — every structural and formatting convention comes from those files, not from general intuition.

### Frontmatter

```yaml
---
campaign_url: /rpg/<campaign-slug>/public/
campaign_name: <campaign.yaml name>
layout: session
title: "Session <N> (<Month> <D>, <YYYY>)"
session_title: "<adventure title from context file>"
adventure: <adventure code from context file>
description: "<one evocative paragraph teaser — not a summary, a hook>"
players:
  - player: <player name>
    character: <character name>
    class: <Race Class Level — use Foundry data if available, else transcript>
image_prompt:
  - "<filled in last — see Achievements section>"
---
```

Session number N = count of existing session pages + 1.

The `description` field is a teaser written in second person or atmospheric present tense — what the session *felt like*, not what happened step by step. Keep it under 50 words.

**`image_prompt` is filled in last**, after all achievement blocks are written in the body. Copy the prompts from the achievements in the exact order they appear on the page. Do not write this list before the body is complete — writing it early is what causes image/achievement mismatches.

### Body narrative

Three to four paragraphs, DM voice, past tense. Cover the full session arc — setup, complications, resolution. Be specific: name dice rolls, name NPCs, name the actual decisions the party made. Do not flatten twists — but also do not guess at things not in the transcript. Where something is unclear, write around it rather than inventing detail.

### Player Highlights

One `<div class="highlight">` per player.

> **Portraits MUST be served from a local copy.** Every portrait `src` (and every character-page `image:`) must point at a file committed under `public/images/portraits/`. **Never** reference an external host — a D&D Beyond avatar URL, a Forge-VTT asset, etc. — directly in a published page. External hosts go down: D&D Beyond periodically drops the entire site into maintenance and every `www.dndbeyond.com/avatars/...` URL 302-redirects to a maintenance page, silently breaking every hotlinked portrait on the live site. Download once, serve our own copy.

Resolve each character's portrait with this priority order:

1. **Local copy already exists** — if `public/images/portraits/<slug>.*` is present, use `/rpg/<campaign-slug>/public/images/portraits/<slug>.<ext>`.
2. **Existing character page `image:`** — if `public/characters/<slug>.md` has an `image:` that is already a local `/rpg/.../images/portraits/...` path, use it as-is. If it is an external URL, treat it as a **source to download** (step 5), not a value to reuse.
3. **`dnd_beyond:` on the character page** — extract the character ID and query the DDB proxy (`POST /proxy/character` with `characterId`) for `.character.decorations.avatarUrl`; that URL is a download source.
4. **Roster / context DDB link** — for characters with no page yet, take the `dnd_beyond:` URL from the context file or roster and query the proxy the same way.
5. **Download to a local copy** — once a source URL is resolved, download it into `public/images/portraits/<slug>.<ext>`. Name the extension to match the **actual bytes**, not the URL: DDB avatar URLs end in `.jpeg?...&auto=webp` but frequently return PNG or WebP, so check the downloaded file's real type (`file --mime-type`) and name it accordingly. Reference the local path everywhere; never the source URL.
6. **Ask the user** — if no source resolves, ask: "No portrait found for <Character>. Do you have a DDB character link or portrait URL?" Do not fall back to the default portrait without asking first.
7. **Default portrait** — only after the user explicitly declines: campaign `default_portrait` from `campaign.yaml`, or the local `/rpg/<campaign>/public/images/default-portrait.png`.

Do the download **before** writing the page, so every `src` you write is already local. If the DDB proxy or D&D Beyond is unreachable when you need a source image, tell the user and pause — do not hotlink as a stopgap.

```html
<div class="highlight">
<img class="highlight-portrait" src="<portrait-url>" alt="<Character> portrait">
<p><strong><a href="../characters/<slug>"><Character></a></strong> (<Player>) — [2–4 sentences. Specific moment, specific roll or quote, specific consequence. No generalities.]</p>
</div>
```

**Always link the highlight name**, even for a character's first appearance: `<strong><a href="../characters/<slug>"><Character></a></strong>`, where `<slug>` is the character name slugified (e.g. `keno-ichikawa`, `zeli-vantel`). Step 5 creates a page for **every** character on the roster — new or returning — so the link target is guaranteed to exist by the time the page is published. Never leave a first-appearance character unlinked; that only happens if you link based on whether the page exists *now* instead of the slug it *will* have.

### Achievements

One `<div class="achievement">` per achievement (3–5 total). Each achievement is a specific moment, quote, or decision from the session — not a general trait. The badge image filename follows the session date and list order.

**Write all achievement blocks here first.** Once they are finalised, go back and fill the `image_prompt` frontmatter list with one entry per achievement, in the same top-to-bottom order as the blocks below. Achievement 1 → image_prompt[0], achievement 2 → image_prompt[1], etc.

```html
<div class="achievement">
<img class="achievement-badge" src="images/<YYYY-MM-DD>-<N>.png" alt="<Achievement Title>">
<p><strong><Achievement Title></strong> — [2–3 sentences describing the exact moment, with any relevant quote or roll.]</p>
</div>
```

### Rewards

Bullet list of gold, downtime, advancement note, streaming hours, and any magic items. Item descriptions should include rarity, attunement requirement if any, and a flavour sentence. Extract from the transcript — do not invent rewards.

## Step 4 — Show the draft and ask for review

Present the full draft to the user. Then say:

"Please review — especially the narrative and achievements. The AI will flatten plot twists and miss things only you know. Tell me anything to correct, add, or cut. Type 'ok' when it's ready to write."

Apply all corrections before proceeding. Re-show only the changed sections, not the full page, unless the user asks.

## Step 5 — Write the session page

Write the approved draft to `public/sessions/YYYY-MM-DD.md`.

## Step 6 — Update site _data/ files

The site root is two levels up from the campaign dir (e.g. `rpg\pandodnd` → `hoshisabi.github.io`). All three known campaign dirs have this layout.

### _data/recent_session.yml

Rewrite the file completely using data from the session page just written:

```yaml
# The "Latest session" teaser on the landing page.
# Update this after each session you want to highlight.
campaign: <campaign.yaml name>
session_label: Session <N>
date: <Month D, YYYY>
title: <session_title frontmatter from session page>
adventure_code: <adventure frontmatter from session page>
href: /rpg/<campaign-slug>/public/sessions/<YYYY-MM-DD>
excerpt: >-
  <description frontmatter from session page, reflowed to ~80 chars>
```

- `campaign-slug` comes from `campaign.yaml slug` (e.g. `icewind-dale`, `pandodnd`)
- `session_label` uses the same N computed in Step 2
- `date` is the human-readable form of the session date: `Month D, YYYY`

### _data/campaigns.yml

Read the file, find the entry in `running:` whose `href` contains the campaign slug, increment its `sessions:` count by 1, then recompute `stats.sessions_logged` as the sum of `sessions:` across all entries in `running:`. Write the file back.

If no matching entry is found, print a warning and skip the update rather than modifying the wrong entry.

## Step 7 — Create or update character pages

Character pages are **per character**, not per player. A player who has appeared before with a different character still gets a fresh page for the new one. The `player:` frontmatter field is the only link between a player and their characters — there are no player pages (may be added later).

For each player character in the roster:

**New character** (no `public/characters/<slug>.md` exists): create the file. The slug is the character name slugified (e.g. `therion-starblade`, `pal-go-lucky`).

Before creating new character pages, resolve DDB links for each new character: check the context file and roster for a `dnd_beyond:` URL; if not present, ask the user: "New characters found — do you have D&D Beyond character links for any of them?" (list the new characters). If the user provides links, use them. If they decline, omit the field. Once you have a `dnd_beyond:` URL, query the DDB proxy for the portrait and **download it to a local copy** as described in the Player Highlights portrait rule — the `image:` field must be the local `/rpg/.../images/portraits/<slug>.<ext>` path, never the DDB/Forge source URL.

```yaml
---
campaign_url: /rpg/<campaign>/public/
campaign_name: <campaign name>
layout: character
title: <Character Name>
player: <Player Name>
class: <Race Class Level>
dnd_beyond: <https://www.dndbeyond.com/characters/<ID> — omit if unknown>
image: </rpg/<campaign>/public/images/portraits/<slug>.<ext> — the LOCAL copy downloaded per the portrait rule, never a DDB/Forge URL; omit only if no portrait exists>
---

## Appearances

- **YYYY-MM-DD** — [Session N (Month D, YYYY)](../sessions/YYYY-MM-DD) (*<session_title>*)

_Note: drop-in roster; this page grows when the character appears in recaps._
```

**Returning character** (page exists): append to its `## Appearances` list only:
```
- **YYYY-MM-DD** — [Session N (Month D, YYYY)](../sessions/YYYY-MM-DD) (*<session_title>*)
```

Do not touch any other content in an existing character page. Do not update pages for characters who did **not** appear in this session.

## Step 8 — Hand off

List the files written. Then:

"Done. Next steps:
1. Generate achievement images — run `/scrollcase-artgen` (or see the commands in the context file)
2. DM debrief — run `/scrollcase-debrief` (or open `<dm-dir>/sessions/YYYY-MM-DD-dm-prompt.md` and paste into a fresh Claude conversation)
3. When both are done, commit and push — include both `rpg/<campaign>/` and `_data/`"

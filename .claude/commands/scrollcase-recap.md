Generate the player-facing session recap page for a scrollcase campaign. Reads the context file and transcript produced by `/scrollcase-prep`, drafts the session page, shows it to the user for review and correction, then writes it.

`$ARGUMENTS` may contain a campaign name (`pandodnd`, `icewind-dale`, `log`) and/or a date (`YYYY-MM-DD`). If omitted, find the most recent context file with no corresponding public session page.

## Paths

| Campaign | Campaign dir |
|---|---|
| pandodnd | `C:\Users\decha\dev\hoshisabi.github.io\rpg\pandodnd` |
| icewind-dale | `C:\Users\decha\dev\hoshisabi.github.io\rpg\icewind-dale` |
| log | `C:\Users\decha\dev\hoshisabi.github.io\rpg\log` |

## Step 1 — Find the context file

Look for `dm/sessions/YYYY-MM-DD-context.md` files in the campaign dir. The target is the most recently created one that has **no** corresponding `public/sessions/YYYY-MM-DD.md`. If `$ARGUMENTS` specifies a date, use that instead.

If multiple campaigns are present and no campaign is specified, check each one and ask the user which to work on.

## Step 2 — Read all the inputs

Read these in parallel:

- The context file (`dm/sessions/YYYY-MM-DD-context.md`) — date, adventure code/title, roster, transcript path
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
  - "<scene-specific prompt for achievement 1 — campaign prefix prepended automatically>"
  - "<scene-specific prompt for achievement 2>"
---
```

Session number N = count of existing session pages + 1.

The `description` field is a teaser written in second person or atmospheric present tense — what the session *felt like*, not what happened step by step. Keep it under 50 words.

Image prompts are scene-specific only. The campaign prefix (from `campaign.yaml image_prompt_prefix`) is prepended automatically at generation time — do not repeat it. Each prompt should describe a single iconic moment or object as a circular badge icon, bold simple shapes, no text. Aim for 3-5 achievements.

### Body narrative

Three to four paragraphs, DM voice, past tense. Cover the full session arc — setup, complications, resolution. Be specific: name dice rolls, name NPCs, name the actual decisions the party made. Do not flatten twists — but also do not guess at things not in the transcript. Where something is unclear, write around it rather than inventing detail.

### Player Highlights

One `<div class="highlight">` per player. Portrait image src: use that character's `image:` from `public/characters/<slug>.md` when set. If the character has no page yet, or the page has no `image:`, use the campaign `default_portrait` from `campaign.yaml`, or `/rpg/<campaign>/public/images/default-portrait.png` as final fallback.

```html
<div class="highlight">
<img class="highlight-portrait" src="<portrait-url>" alt="<Character> portrait">
<p><strong><a href="../characters/<slug>"><Character></a></strong> (<Player>) — [2–4 sentences. Specific moment, specific roll or quote, specific consequence. No generalities.]</p>
</div>
```

If a character has no existing page yet, omit the `<a>` link for now and use just `<strong><Character></strong>` — you'll create the page in Step 5.

### Achievements

One `<div class="achievement">` per achievement (3–5 total). Each achievement is a specific moment, quote, or decision from the session — not a general trait. The badge image filename follows the session date and list order.

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

## Step 6 — Create or update character pages

Character pages are **per character**, not per player. A player who has appeared before with a different character still gets a fresh page for the new one. The `player:` frontmatter field is the only link between a player and their characters — there are no player pages (may be added later).

For each player character in the roster:

**New character** (no `public/characters/<slug>.md` exists): create the file. The slug is the character name slugified (e.g. `therion-starblade`, `pal-go-lucky`).

```yaml
---
campaign_url: /rpg/<campaign>/public/
campaign_name: <campaign name>
layout: character
title: <Character Name>
player: <Player Name>
class: <Race Class Level>
image: <portrait URL if known, else omit>
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

## Step 7 — Hand off

List the files written. Then:

"Done. Next steps:
1. Generate achievement images — run `/scrollcase-artgen` (or see the commands in the context file)
2. DM prep — open `dm/sessions/YYYY-MM-DD-dm-prompt.md` and paste into a fresh Claude conversation
3. When both are done, commit and push `rpg/<campaign>/`"

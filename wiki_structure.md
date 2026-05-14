# Wiki Structure

Markdown documents that grow over time and serve as context for future DM assistant prompts.
Stored in the campaign's git repo alongside session logs.

## Directory layout

```
campaign/
  dm/                                       # DM-only; never published
    character-sheets/
      [name].pdf                            # PC character sheets
    characters/
      pcs/
        images/
        oskar.md                            # one file per PC
        kaelisa.md
        cinder.md
        araken.md
      npcs/
        images/
        [name].md                           # one file per notable NPC
    factions/
      [name].md                             # organizations, cults, tribes, etc.
    locations/
      [name].md                             # full location details (DM view)
    sessions/
      YYYY-MM-DD-dm-assistant.md            # DM assistant report per session
      session_transcript_MMDDYY.txt         # raw corrected transcript
    threads.md                              # active plot hooks; mark resolved with date
    timeline.md                             # session-by-session event log, one line per beat
  public/                                   # published to GitHub Pages
    index.md
    characters/                             # PCs only
      images/
      [name].md
    npcs/                                   # notable NPCs (selectively published)
      images/
      [name].md
    locations/
      images/
      [name].md
    sessions/
      YYYY-MM-DD.md                         # player-facing recap
```

## Session log front matter

Public session recaps (`public/sessions/YYYY-MM-DD.md`) use this front matter:

```yaml
---
layout: default
title: "Session N (Month D, YYYY)"
session_title: "Evocative Chapter Name"
description: "One or two sentences of narrative prose — written like a hook, not a bullet list."
---

# Session N (Month D, YYYY)
```

- `title`: `Session N (Month D, YYYY)` — parentheses, not em dash
- `session_title`: short evocative name (think chapter title); required — the index renders it as `title — session_title`
- `description`: narrative prose, present or past tense, written for a reader who wasn't there
- H1 heading must match `title` exactly

## Session page body structure

After the H1, the session page body follows this order:

1. Narrative recap (the main content — story prose and player highlights)
2. Achievements section (if any)
3. Rewards section (always present)

### Rewards section format

```markdown
## Rewards

| | |
|---|---|
| Adventure | PS-DC-PUB-08 Unremembered Things |
| Downtime | 10 days |
| Gold | 350 gp |
| Level | Optional |

### Magic Items
- **Ioun Stone of Awareness** *(rare, requires attunement)* — Dark-blue rhomboid. Grants Advantage on Initiative rolls and Wisdom (Perception) checks while orbiting.
- **Potion of Greater Healing**

### Story Items
- **Cursed Crystal** — Contains a terrible secret that could not be destroyed; only trapped. Inert until an unknown condition is met.
```

Notes:
- Adventure row matches the AL scenario code + title
- Level row: use "Optional" if the player can choose, omit if not awarded
- Magic Items: include rarity, attunement requirement, and the mechanical effect in brief
- Story Items: items with narrative weight but no standard stat block entry — describe the hook

## Document conventions

### Character files (PCs and NPCs)
- Known facts only — what the party knows, not DM secrets
- Updated after each session that advances the character
- Sections: Description, Known History, Relationships, Session Notes (brief per-session bullet)

### Location files
- First visited date
- What the party observed/learned
- Known connections to other locations or factions
- Open questions

### threads.md
- One bullet per thread
- Format: `- [ACTIVE/RESOLVED YYYY-MM-DD] **Thread name**: description`

### timeline.md
- One line per significant event, chronological
- Format: `- [Session YYYY-MM-DD] Brief description of event`

## How to use with prompts

For each new session, feed the prompt:
- Full transcript
- All PC files
- Any NPC files for characters who appeared
- Any location files for places visited
- threads.md
- Previous session summary (optional, for continuity)

When the wiki is large, select only relevant documents rather than dumping everything.
After generating the report, update wiki files to reflect new session info.

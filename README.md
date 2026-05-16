# scrollcase

Turns session recordings into a living campaign record.

## Campaigns

| Directory | Campaign | DM | Type |
|---|---|---|---|
| `rpg/icewind-dale/` | Icewind Dale | Dan | in-person campaign |
| `rpg/pandodnd/` | PandoDnD Online Campaign | Dan | drop-in one-shots |
| `rpg/log/` | Legends of Greyhawk | Bryan | campaign (Dan plays) |

Each campaign directory contains a `campaign.yaml` with its settings.

### Campaign directory paths (for `--campaign-dir`)

```
Icewind Dale:  C:\Users\decha\dev\hoshisabi.github.io\rpg\icewind-dale
PandoDnD:      C:\Users\decha\dev\hoshisabi.github.io\rpg\pandodnd
Greyhawk:      C:\Users\decha\dev\hoshisabi.github.io\rpg\log
```

`--campaign-dir` on the command line always overrides the `CAMPAIGN_DIR` env var.

---

## PandoDnD weekly workflow

### Before the session
- At the start, say the roster out loud: *"We have Michael playing Sparrow, Don playing Pal Go Lucky..."*
  This makes extraction reliable and avoids guesswork on opaque Discord handles.

### After the session (7-day clock — NoteCat free tier)
1. Download the **NoteCat markdown** from Discord
2. Download the **audio** too (cheap insurance, storage is cheap)

### Processing

**Step 1 — Run the prep script**

```
cd C:\Users\decha\dev\miscprojects\scrollcase
uv run python process_session.py "D:\downloads\<notecat-file>.md" --campaign-dir "C:\Users\decha\dev\hoshisabi.github.io\rpg\pandodnd"
```

The script handles:
- Parsing the NoteCat markdown (date, speakers, intro)
- Warhorn lookup → adventure scenario
- Adventure catalog lookup → code, title, metadata
- Interactive roster questions (one per speaker)
- Player registry update (`dm/player-registry.yaml`)
- Writes `dm/sessions/YYYY-MM-DD-roster.md`
- Writes `dm/sessions/YYYY-MM-DD-context.md` — the handoff to Claude Code

**Step 2 — Bring into Claude Code**

Open a Claude Code conversation, share the context file path, and ask Claude to:
1. Read the context file and the NoteCat transcript
2. Confirm/correct the roster
3. Generate the session recap, player highlights, and achievements
4. Write the public session page to `public/sessions/YYYY-MM-DD.md`

**Step 3 — DM review**

Read the draft. Correct anything the AI got wrong about the plot — it will always
flatten twists and miss things only you know. This is the most important step.

**Step 4 — Achievement images** *(optional)*

Once achievement image prompts are confirmed in the session page:

```
uv run python process_session.py --generate-images YYYY-MM-DD --campaign-dir "C:\Users\decha\dev\hoshisabi.github.io\rpg\pandodnd"
```

**Step 5 — Publish**

```
cd C:\Users\decha\dev\hoshisabi.github.io
git add rpg/pandodnd/
git commit -m "session YYYY-MM-DD"
git push
```

---

## Setup

### .env (in this directory)
```
WARHORN_APPLICATION_TOKEN=...
CAMPAIGN_DIR=C:\Users\decha\dev\hoshisabi.github.io\rpg\pandodnd
AL_CATALOG_DIR=C:\Users\decha\dev\al_adventure_catalog\maintaindb\_dc
GOOGLE_KEY=...
```

### First run
```
uv sync
```

---

## What the AI gets wrong (known patterns)

- **Plot twists** — the AI summary flattens them. Always tell Claude what actually happened.
- **Character names** — players don't always say them in intros. The script will ask.
- **Who actually played** — speakers who left before the session started show up in the list. Skip them at the roster prompt.
- **Opaque Discord handles** — `markd_39290` tells you nothing. Say the roster out loud at session start.

---

## Files produced per session

| File | Contents |
|---|---|
| `dm/sessions/YYYY-MM-DD-roster.md` | Full roster with Discord handles |
| `dm/sessions/YYYY-MM-DD-context.md` | Handoff summary for Claude Code |
| `public/sessions/YYYY-MM-DD.md` | Player-facing session page |
| `public/sessions/images/YYYY-MM-DD-*.png` | Achievement badge images |

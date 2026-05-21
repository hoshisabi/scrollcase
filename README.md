# scrollcase

Turns session recordings into a living campaign record.

## Campaigns

| Directory | Campaign | DM | Type |
|---|---|---|---|
| `rpg/icewind-dale/` | Icewind Dale | Dan | in-person campaign |
| `rpg/pandodnd/` | PandoDnD Online Campaign | Dan | drop-in one-shots |
| `rpg/log/` | Legends of Greyhawk | Bryan | campaign (Dan plays) |

Each campaign directory contains a `campaign.yaml` with its settings. Optional **`default_portrait`**: site-root URL for the generic character portrait used when a wiki page or session highlight has no **`image`**. If omitted, the site and tooling use **`/rpg/<slug>/public/images/default-portrait.png`**; scrollcase can copy **`assets/default-portrait.png`** into that path on first `process_session.py` run.

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

Non-interactive (Claude Code skill pre-fills a roster YAML):

```
uv run python process_session.py "<notecat-file>.md" --campaign-dir "<campaign>" \
  --roster-file dm/sessions/YYYY-MM-DD-roster-input.yaml \
  --scenario-name "PS-DC-PUB-08 Unremembered Things" \
  --noprompt
```

`--noprompt` exits with an error if any speaker is missing from `--roster-file` or catalog/Warhorn data is still needed. `--scenario-name` is used when Warhorn lookup fails or is skipped (ignored when Warhorn returns a scenario).

The script handles:
- Parsing the NoteCat markdown (date, speakers, intro)
- Warhorn lookup → adventure scenario
- Adventure catalog lookup → code, title, metadata
- Interactive roster questions (one per speaker)
- Player registry update (`dm/player-registry.yaml`)
- Writes `dm/sessions/YYYY-MM-DD-roster.md`
- Writes `dm/sessions/YYYY-MM-DD-context.md` — the handoff to Claude Code

**Step 2 — Player recap (Claude Code)**

Open a Claude Code conversation, share the context file path, and ask Claude to:
1. Read the context file and the NoteCat transcript
2. Confirm/correct the roster
3. Generate the session recap, player highlights, and achievements
4. Write the public session page to `public/sessions/YYYY-MM-DD.md`

**Step 3 — DM prep (fresh Claude conversation)**

Open a fresh Claude conversation (not Claude Code — this is a paste workflow).
Open `dm/sessions/YYYY-MM-DD-dm-prompt.md` and paste its contents.
Save Claude's response to `dm/sessions/YYYY-MM-DD-prep.md`.

The prompt is pre-filled with your DM name, campaign, date, players, and the paths
to your wiki files (threads, timeline, PCs, NPCs) and transcript. Claude will produce:
- Session summary in DM voice
- Narrative threads, unresolved tensions
- Player engagement notes and spotlight opportunities
- Pacing advice and prep recommendations for next session
- Ready-to-use encounter/scene tools

After saving the prep report, update `dm/threads.md` and `dm/timeline.md` with
anything new from this session.

**Step 4 — DM review**

Read the player recap draft. Correct anything the AI got wrong about the plot — it
will always flatten twists and miss things only you know. This is the most important step.

**Step 5 — Achievement images** *(optional)*

Once achievement image prompts are on the session page (`image_prompt` in YAML frontmatter, or legacy HTML comments — see **`style_guide.md`**), generate images with either command; filenames are the same (`public/sessions/images/`).

```
uv run python process_session.py --generate-images YYYY-MM-DD --campaign-dir "C:\Users\decha\dev\hoshisabi.github.io\rpg\pandodnd"
```

```
uv run python generate_artwork.py public/sessions/YYYY-MM-DD.md
```

Shield-shaped achievement crop (post-process):

```
uv run python process_session.py --generate-images YYYY-MM-DD --badge --campaign-dir "C:\Users\decha\dev\hoshisabi.github.io\rpg\pandodnd"
```

```
uv run python generate_artwork.py public/sessions/YYYY-MM-DD.md --badge
```

Apply the shield crop to existing PNGs without calling Imagen:

```
uv run python generate_artwork.py --badge-only public/sessions/YYYY-MM-DD.md
```

Overwrite existing PNGs during generation with `--force` on either script (`process_session.py` only accepts `--force` together with `--generate-images`).

**Older session pages:** Earlier versions of `--generate-images` wrote `YYYY-MM-DD-achievement-N.png`. Canonical names are now `YYYY-MM-DD.png` (single prompt) or `YYYY-MM-DD-1.png`, `YYYY-MM-DD-2.png`, … per **`style_guide.md`**. Rename old files and update `<img src=…>` once if you still have the legacy filenames.

**Step 6 — Publish**

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

| File | Who writes it | Contents |
|---|---|---|
| `dm/sessions/YYYY-MM-DD-roster.md` | Script | Full roster with Discord handles |
| `dm/sessions/YYYY-MM-DD-context.md` | Script | Handoff summary for Claude Code (player recap) |
| `dm/sessions/YYYY-MM-DD-dm-prompt.md` | Script | Pre-filled DM assistant prompt — paste into Claude |
| `dm/sessions/YYYY-MM-DD-prep.md` | Claude (you paste) | DM prep report: threads, player notes, next-session guidance |
| `dm/sessions/YYYY-MM-DD-debrief.md` | You | Post-session notes: what actually happened, corrections |
| `public/sessions/YYYY-MM-DD.md` | Claude Code | Player-facing session page |
| `public/sessions/images/YYYY-MM-DD-*.png` | Script | Achievement badge images |

### dm/ living documents (update after each session)

| File | Contents |
|---|---|
| `dm/threads.md` | All active/resolved/background plot threads — the cold-start context doc |
| `dm/timeline.md` | Flat chronological event log |

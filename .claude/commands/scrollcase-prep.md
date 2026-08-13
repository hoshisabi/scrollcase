Process a TTRPG session through scrollcase: find unprocessed files in the inbox, identify the campaign, build the roster interactively, run the prep pipeline non-interactively, then move files into the campaign subfolder as a completion signal.

`$ARGUMENTS` may contain a campaign name (`pandodnd`, `icewind-dale`, `log`), a date (`YYYY-MM-DD`), a filesystem path to a source directory, or any combination — use them to narrow the search. If omitted, auto-detect.

`$ARGUMENTS` may **also** carry free-form DM details that are not inputs to the script — session rewards (gold, magic items and their property text, downtime, streaming hours) and name/lore spellings. These are not passed to `process_session.py`; hold onto them and record them in the context file in Step 11 so the recap and debrief pick them up automatically.

## Paths

| Thing | Path |
|---|---|
| Inbox (unprocessed) | Google Drive `scrollcase` folder, mounted as **`D:\GoogleDrive\chapmand\My Drive\scrollcase\`** *or* **`H:\My Drive\scrollcase\`** depending on the machine (same folder, different drive letter) — probe both, use whichever exists |
| pandodnd campaign | `C:\Users\decha\dev\hoshisabi.github.io\rpg\pandodnd` |
| icewind-dale campaign | `C:\Users\decha\dev\hoshisabi.github.io\rpg\icewind-dale` |
| log campaign | `C:\Users\decha\dev\hoshisabi.github.io\rpg\log` |
| pandodnd DM dir | `C:\Users\decha\dev\hoshisabi-dm\pandodnd` |
| icewind-dale DM dir | `C:\Users\decha\dev\hoshisabi-dm\icewind-dale` |
| log DM dir | `C:\Users\decha\dev\hoshisabi-dm\log` |
| scrollcase scripts | `C:\Users\decha\dev\scrollcase` |

The **campaign dir** (passed as `--campaign-dir`) is the public site path — it contains `campaign.yaml` and `public/`. The **DM dir** (passed as `--dm-dir`) is the private repo path — it contains `sessions/`, `player-registry.yaml`, and `characters/`.

## Step 1 — Find unprocessed files

Determine the **source directory**:
- If `$ARGUMENTS` is a filesystem path (contains `\` or `/`, or starts with a drive letter), use it as the source directory.
- Otherwise use the standard inbox. The inbox is a Google Drive folder that maps to a **different drive letter on different machines** — `D:\GoogleDrive\chapmand\My Drive\scrollcase\` on some, `H:\My Drive\scrollcase\` on others. **Do not assume `D:` — probe both and use whichever exists:**

```powershell
$inbox = @(
  "D:\GoogleDrive\chapmand\My Drive\scrollcase",
  "H:\My Drive\scrollcase"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
```

If neither exists, say so and stop.

List all transcript files **directly in the source directory** (not in subfolders). Transcripts are `.md` files (NoteCat) or `.txt` files (SessionKeeper). These are unprocessed sessions.

- If `$ARGUMENTS` contains a date, narrow to files whose name contains that date.
- If `$ARGUMENTS` contains **no** date and more than one file is present, first offer a **date choice** to narrow — AskUserQuestion, header **Date**, options: **Today** (the current date), **Yesterday** (current date − 1 day), **Enter a date** (`YYYY-MM-DD`). Resolve Today/Yesterday to a concrete `YYYY-MM-DD` using the current system date, then narrow to files whose name contains it. This narrows the file search only — the authoritative session date still comes from the transcript in Step 3.
- If none are found, say so and stop.
- If exactly one is found, proceed with it.
- If 2-4 are found, use AskUserQuestion — question: "Which session should I process?", header: "Session", one option per filename.
- If more than 4 are found, list them and ask in chat which to process.

Also collect any companion files in the source directory: audio files (`.ogg`, `.aac`, `.m4a`) and `fvtt-Actor-*.json` Foundry exports. These travel with the session. A single session may have **more than one** audio file — e.g. a raw `recording-*.ogg` plus an `optimized_*.m4a` — and both belong to it, since there is only ever one transcript per session.

## Step 2 — Detect format and campaign

Read the first 30 lines of the transcript file.

**Format detection:**
- NoteCat format: contains `**Date**:` and `**Duration**:` headers, speakers appear as `**Handle** - HH:MM PM`
- SessionKeeper/raw format: speakers appear as `Speaker Name: text` lines

**Campaign inference:**
- NoteCat → almost certainly `pandodnd` (it's the only online campaign using NoteCat)
- SessionKeeper → `icewind-dale` or `log` — use session content/character names as hints if possible

If `$ARGUMENTS` names a campaign, use it. Otherwise propose your best guess and use AskUserQuestion:

- question: "Which campaign is this session for?"
- header: "Campaign"
- options: best guess first, marked "(Recommended)", then the other two campaign names (`pandodnd`, `icewind-dale`, `log`)

## Step 3 — Read the transcript

Read the first 120 lines of the file. Extract:
- Session date (from `**Date**:` header for NoteCat; from filename or content for raw — SessionKeeper filenames often encode the date as `MMDDYY`, e.g. `session_transcript_053026.txt` → 2026-05-30)
- Speaker list — deduplicated, in order of first appearance
  - NoteCat: the `**Handle**` names from speaker lines (not italicised presence lines)
  - Raw: the `Name:` prefixes from dialogue lines
- Summary section if present (NoteCat) — often names characters directly
- Any character introduction lines in the opening transcript

## Step 4 — Extract Foundry character data (if JSONs present)

For each `fvtt-Actor-*.json` in the source directory, use PowerShell to extract key fields. Files are large — do not read directly; use `ConvertFrom-Json` and select only what you need. Run all extractions in parallel:

```powershell
$j    = Get-Content "<path>" -Raw | ConvertFrom-Json
$char = $j.name
$race = $j.items | Where-Object { $_.type -eq 'race' }       | Select-Object -First 1 -ExpandProperty name
$cls  = $j.items | Where-Object { $_.type -eq 'class' }      | ForEach-Object { "$($_.name) $($_.system.levels)" }
$sub  = $j.items | Where-Object { $_.type -eq 'subclass' }   | Select-Object -First 1 -ExpandProperty name
$ab   = $j.system.abilities
$hp   = "$($j.system.attributes.hp.value)/$($j.system.attributes.hp.max)"
```

Build a lookup table keyed by character name for use in roster building.

### DDB proxy — authoritative character data

Use the DDB proxy to fetch authoritative character data **whenever a DDB character ID is known from any source** — a Foundry JSON, a link the user provided, or a prior session / character page (see Step 5b). It is **not** gated on Foundry being present; drop-in campaigns usually have no Foundry exports but still have DDB IDs in the repo. When both DDB and Foundry data exist, **always prefer DDB** — Foundry exports can be stale (wrong level, subclass, or race). DDB also fixes the phonetic misspellings the transcript introduces (e.g. "Z'lai Ventel" → **Zeli Vantel**, "Terry" → **Tarrie**).

**Check the proxy is up:** `Invoke-RestMethod http://localhost:3000/ping` → returns `pong`. If it does **not** respond and you have DDB IDs to verify, tell the user the proxy is down and ask them to start it, then re-check — don't silently skip verification when DDB IDs are in play.

**Extract the DDB character ID from each Foundry JSON:**
```powershell
$ddbId = $j.flags.ddbimporter.dndbeyond.characterId
```

**Fetch all characters in parallel:**
```powershell
$body = @{ characterId = $ddbId; cobalt = $cobalt } | ConvertTo-Json
$r = Invoke-RestMethod "http://localhost:3000/proxy/character" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 15
$c = $r.ddb.character
$name    = $c.name
$race    = $c.race.fullName
$classes = ($c.classes | ForEach-Object { "$($_.definition.name) Lv$($_.level) [$($_.subclassDefinition.name)]" }) -join " / "
```

**Cobalt token:** stored in `C:\Users\decha\dev\ddb-proxy\.env`. For public characters an empty string works (`$cobalt = ""`). To load it cleanly from the file in PowerShell:
```powershell
$cobalt = (Get-Content "C:\Users\decha\dev\ddb-proxy\.env" |
           Where-Object { $_ -match '^[^#].*=' } |
           Select-Object -First 1) -replace '^[^=]+=', '' -replace '"', ''
```
Or with Python's dotenv if you need it in a script context:
```python
from dotenv import load_dotenv
load_dotenv(r"C:\Users\decha\dev\ddb-proxy\.env")
cobalt = os.getenv("COBALT_TOKEN", "")
```

## Step 5 — Load the player registry

Read `<dm-dir>/player-registry.yaml`. Build a lookup: discord alias → registry entry (slug, display_name). If the file doesn't exist yet, treat it as empty.

## Step 5b — Resolve known characters from repo history

Drop-in campaigns (`pandodnd`, `log`) have no pre-registered PC files, but most characters have appeared before and their DDB links already live in the repo. **Before asking the user for anything, look them up:**

1. **Prior sessions** — grep the DM dir for the character name to find a `ddb_id`:
   `<dm-dir>/sessions/*-roster-input.yaml` (has `ddb_id:` next to `character_name:`) and `*-context.md` (has `([DDB](https://www.dndbeyond.com/characters/<id>))`).
2. **Character pages** — `<campaign-dir>/public/characters/*.md`. Each has a `title:` (character name) and `dnd_beyond:` link. Match the transcript's character name against `title:`.

```powershell
# example: sweep both sources for DDB links, then eyeball by character name
Select-String -Path "<dm-dir>\sessions\*-context.md","<dm-dir>\sessions\*-roster-input.yaml" -Pattern "dndbeyond.com/characters/\d+|ddb_id"
Select-String -Path "<campaign-dir>\public\characters\*.md" -Pattern "^title:|dnd_beyond:"
```

Because transcript character names are phonetic, **match loosely and let the existing spelling win** — e.g. transcript "Perry" → page `perri.md` (**Perri**), "Terry" → **Tarrie**, "Azar Alnar" → **Azhar al-Nar**. Adopt the repo's spelling and its DDB link.

Then, for every `ddb_id` you resolved (plus any the user supplied), **verify via the DDB proxy** (Step 4) to confirm the current name, race, class, and level. Only characters with no repo match and no proxy hit stay as `?` in the roster — ask the user for *those* DDB links specifically, rather than asking about the whole roster.

## Step 6 — Propose the roster

For each speaker, combine what you know:
- Repo history (drop-in campaigns) → DDB link + canonical character spelling from prior sessions and `<campaign-dir>/public/characters/*.md` (see Step 5b); resolve this **before** marking anyone unknown
- Registry match on discord alias → known player name and slug
- Character files at `<dm-dir>/characters/pcs/` — read matching files for class, race, and full character name
- Summary/intro lines → character name hint
- Foundry JSON → character name, class, race (match by name similarity or intro mention); **DDB proxy data overrides Foundry when both are available** — see Step 4
- Campaign DM (from `campaign.yaml` `dm:` field) — the DM won't have a Foundry export; for NoteCat, their handle is often a real name like "Dan Chapman (he/him)"
- For **raw/SessionKeeper format**: speakers are character names already; roster work is mainly confirming class/race from character files and flagging the DM

Present the proposed roster as a table:

```
Proposed roster for YYYY-MM-DD — confirm or correct:

| # | Discord handle         | Player | Character      | Class              | DDB        | DM? |
|---|------------------------|--------|----------------|--------------------|------------|-----|
| 1 | Dan Chapman (he/him)   | Dan    | —              | —                  | —          | yes |
| 2 | Ken B. (Neko)          | Ken    | Nico           | Druid/Ranger/Monk  | 113570473  | no  |
| 3 | MarkD                  | Mark   | Therion        | Fighter            | 162592792  | no  |
| 4 | unknownhandle          | ?      | ?              | ?                  | ?          | no  |

Show the DDB column so resolved links (Step 5b) are visible for confirmation and any `?` makes the gap obvious.
```

Then use AskUserQuestion:

- question: "Does this roster look correct?"
- header: "Roster"
- options:
  - "Yes, looks good" (Recommended)
  - "I need to make corrections" — ask in chat what to fix (e.g. "4 is Michael playing Sparrow, a Rogue" or "3 is the DM"), apply conversationally, re-show the table, and ask this question again

## Step 7 — Confirm the scenario name

Derive a readable name from the transcript title or filename (e.g. `Bitopia_Doomometer_Pub_Crawl_2026-05-20.md` → "Bitopia Doomometer Pub Crawl"). This is passed as `--scenario-name` as a Warhorn fallback.

Use AskUserQuestion:

- question: "Scenario name?"
- header: "Scenario"
- options:
  - "Use '<derived>'" (Recommended)
  - "I'll type a different name" — if chosen (or if the user picks "Other" with a name directly), use the provided name

Skip this step for campaigns without Warhorn (`icewind-dale`, `log`) — pass an empty or omitted `--scenario-name`.

## Step 8 — Write the roster input file

Write `<dm-dir>/sessions/YYYY-MM-DD-roster-input.yaml`:

```yaml
- discord_name: "exact handle as it appears in the transcript"
  player_name: Dan
  is_dm: true

- discord_name: "Ken B. (Neko)"
  player_name: Ken
  character_name: Nico
  character_class: Druid/Ranger/Monk
  is_dm: false
  slug: kenb        # omit for new players if unknown; the script will derive it
  ddb_id: 113570473 # numeric ID from the DnD Beyond character URL
```

Rules:
- `discord_name` must exactly match the speaker string from the transcript
- `slug` for known registry players: use the existing slug
- `slug` for new players: derive from first word of `player_name` (lowercased); ask if a collision is likely
- DM entry: `is_dm: true`, no `character_name`, `character_class`, `slug`, or `ddb_id`
- `ddb_id`: the numeric ID from the D&D Beyond character URL (`dndbeyond.com/characters/<id>`). Populate this whenever a DDB link is provided by the user or fetched via the DDB proxy. Omit if unknown.
- Omit optional fields rather than leaving them blank

Show the file contents, then use AskUserQuestion:

- question: "Ready to run the pipeline?"
- header: "Run"
- options:
  - "Yes, run it" (Recommended)
  - "No, let me make changes first"

## Step 9 — Run the pipeline

```powershell
$env:PYTHONUTF8 = "1"
cd C:\Users\decha\dev\scrollcase
uv run python process_session.py "<source-transcript-path>" `
  --campaign-dir "<campaign-dir>" `
  --dm-dir "<dm-dir>" `
  --roster-file "<dm-dir>\sessions\YYYY-MM-DD-roster-input.yaml" `
  --scenario-name "<confirmed name>" `
  --noprompt
```

For campaigns without Warhorn, omit `--scenario-name`.

Show the output. If the script errors, report the message and stop — do not retry automatically. A `--noprompt` error means a question wasn't pre-answered; tell the user which one and ask how to resolve it.

## Step 10 — Move files to campaign subfolder

**Only applies when the source directory is the scrollcase inbox root** — i.e., the files were found directly in the scrollcase folder (not already in a campaign subfolder). The inbox may be mounted as `D:\GoogleDrive\chapmand\My Drive\scrollcase\` or `H:\My Drive\scrollcase\` depending on the machine; what matters is that the source directory's parent is not already a campaign subfolder (`pandodnd`, `icewind-dale`, `log`).

On success, move all files that were collected in Step 1 to the campaign subfolder:

```powershell
$dest = "<inbox-root>\<campaign>\"
Move-Item "<inbox-root>\<transcript>" $dest
# move any audio and fvtt-Actor-*.json files collected in Step 1
```

Only move the files identified in Step 1 — do not sweep the entire root in case another session was dropped in while this one was being processed.

**After moving, update the context file** to point to the new transcript location:

```powershell
(Get-Content "<dm-dir>\sessions\YYYY-MM-DD-context.md") `
  -replace [regex]::Escape("<old-transcript-path>"), "<new-transcript-path>" |
  Set-Content "<dm-dir>\sessions\YYYY-MM-DD-context.md" -Encoding UTF8
```

Confirm the replacement printed the updated path.

## Step 11 — Record DM-provided details in the context file

The pipeline writes `<dm-dir>/sessions/YYYY-MM-DD-context.md`, but it only knows what the script produced — it does **not** capture the reward/lore/note text from `$ARGUMENTS` or anything the user added during roster building. Those matter downstream (recap loot lists, correct NPC spellings), so append them to the context file now.

Insert a section just before the `---` / "Next step" divider:

```markdown
## DM-provided details (not in transcript / spelling reference)

**Rewards** (per PC unless noted):
- <gold, items + full property text, downtime, streaming hours>

**Name spellings (original NPCs / lore):**
- <NPC / deity / place names with correct spelling and any backstory the DM gave>
```

Follow the campaign's reward conventions (e.g. for Adventurers League, items are shared-pool **unlocks**, not assigned to a PC). If the user supplied no such details, skip this step.

## Step 12 — Hand off

List the files written by the script (it prints them) and confirm any files were moved. Then:

"Prep complete. Each of these runs in a fresh conversation and reads the context file itself — nothing to copy-paste:
- Player recap → `/scrollcase-recap <campaign> <date>`
- DM debrief → `/scrollcase-debrief <campaign> <date>`"

(Fill in the actual campaign slug and `YYYY-MM-DD` so the user can run them verbatim.)

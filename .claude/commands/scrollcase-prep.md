Process a TTRPG session through scrollcase: find unprocessed files in the inbox, identify the campaign, build the roster interactively, run the prep pipeline non-interactively, then move files into the campaign subfolder as a completion signal.

`$ARGUMENTS` may contain a campaign name (`pandodnd`, `icewind-dale`, `log`), a date (`YYYY-MM-DD`), or both — use them to narrow the search. If omitted, auto-detect.

## Paths

| Thing | Path |
|---|---|
| Inbox (unprocessed) | `D:\GoogleDrive\chapmand\My Drive\scrollcase\` |
| pandodnd campaign | `C:\Users\decha\dev\hoshisabi.github.io\rpg\pandodnd` |
| icewind-dale campaign | `C:\Users\decha\dev\hoshisabi.github.io\rpg\icewind-dale` |
| log campaign | `C:\Users\decha\dev\hoshisabi.github.io\rpg\log` |
| scrollcase scripts | `C:\Users\decha\dev\miscprojects\scrollcase` |

## Step 1 — Find unprocessed files

List all `.md` files **directly in the inbox root** (not in subfolders). These are unprocessed sessions.

- If `$ARGUMENTS` contains a date, narrow to files whose name contains that date.
- If multiple `.md` files are found, show the list and ask the user which to process.
- If none are found, say so and stop.

Also collect any other files in the inbox root: `.ogg` audio files and `fvtt-Actor-*.json` Foundry exports. These travel with the session and will be moved at the end.

## Step 2 — Detect format and campaign

Read the first 30 lines of the transcript file.

**Format detection:**
- NoteCat format: contains `**Date**:` and `**Duration**:` headers, speakers appear as `**Handle** - HH:MM PM`
- SessionKeeper/raw format: speakers appear as `Speaker Name: text` lines

**Campaign inference:**
- NoteCat → almost certainly `pandodnd` (it's the only online campaign using NoteCat)
- SessionKeeper → `icewind-dale` or `log` — use session content/character names as hints if possible

If `$ARGUMENTS` names a campaign, use it. Otherwise propose your best guess and ask: "This looks like a **pandodnd** session — correct? (or type the campaign name)"

## Step 3 — Read the transcript

Read the first 120 lines of the file. Extract:
- Session date (from `**Date**:` header for NoteCat; from filename or content for raw)
- Speaker list — deduplicated, in order of first appearance
  - NoteCat: the `**Handle**` names from speaker lines (not italicised presence lines)
  - Raw: the `Name:` prefixes from dialogue lines
- Summary section if present (NoteCat) — often names characters directly
- Any character introduction lines in the opening transcript

## Step 4 — Extract Foundry character data (if JSONs present)

For each `fvtt-Actor-*.json` in the inbox root, use PowerShell to extract key fields. Files are large — do not read directly; use `ConvertFrom-Json` and select only what you need. Run all extractions in parallel:

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

## Step 5 — Load the player registry

Read `<campaign-dir>/dm/player-registry.yaml`. Build a lookup: discord alias → registry entry (slug, display_name). If the file doesn't exist yet, treat it as empty.

## Step 6 — Propose the roster

For each speaker, combine what you know:
- Registry match on discord alias → known player name and slug
- Summary/intro lines → character name hint
- Foundry JSON → character name, class, race (match by name similarity or intro mention)
- Campaign DM (from `campaign.yaml` `dm:` field) — the DM won't have a Foundry export; for NoteCat, their handle is often a real name like "Dan Chapman (he/him)"
- For **raw/SessionKeeper format**: speakers are already real names, so roster work is lighter — mainly confirm character names and flag the DM

Present the proposed roster as a table and ask the user to confirm or correct it:

```
Proposed roster for YYYY-MM-DD — confirm or correct:

| # | Discord handle         | Player | Character      | Class              | DM? |
|---|------------------------|--------|----------------|--------------------|-----|
| 1 | Dan Chapman (he/him)   | Dan    | —              | —                  | yes |
| 2 | Ken B. (Neko)          | Ken    | Nico           | Druid/Ranger/Monk  | no  |
| 3 | MarkD                  | Mark   | Therion        | Fighter            | no  |
| 4 | unknownhandle          | ?      | ?              | ?                  | no  |

Correct anything that's wrong — e.g. "4 is Michael playing Sparrow, a Rogue" or "3 is the DM".
Type "ok" when done.
```

Apply corrections conversationally. Re-show the table if anything changed. Repeat until "ok".

## Step 7 — Confirm the scenario name

Derive a readable name from the transcript title or filename (e.g. `Bitopia_Doomometer_Pub_Crawl_2026-05-20.md` → "Bitopia Doomometer Pub Crawl"). This is passed as `--scenario-name` as a Warhorn fallback.

Ask: "Scenario name — press Enter to use `<derived>`, or type the correct one:"

Skip this step for campaigns without Warhorn (`icewind-dale`, `log`) — pass an empty or omitted `--scenario-name`.

## Step 8 — Write the roster input file

Write `<campaign-dir>/dm/sessions/YYYY-MM-DD-roster-input.yaml`:

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
```

Rules:
- `discord_name` must exactly match the speaker string from the transcript
- `slug` for known registry players: use the existing slug
- `slug` for new players: derive from first word of `player_name` (lowercased); ask if a collision is likely
- DM entry: `is_dm: true`, no `character_name`, `character_class`, or `slug`
- Omit optional fields rather than leaving them blank

Show the file contents and ask: "Ready to run? (yes / no)"

## Step 9 — Run the pipeline

```powershell
cd C:\Users\decha\dev\miscprojects\scrollcase
uv run python process_session.py "<inbox-transcript-path>" `
  --campaign-dir "<campaign-dir>" `
  --roster-file "<campaign-dir>\dm\sessions\YYYY-MM-DD-roster-input.yaml" `
  --scenario-name "<confirmed name>" `
  --noprompt
```

For campaigns without Warhorn, omit `--scenario-name`.

Show the output. If the script errors, report the message and stop — do not retry automatically. A `--noprompt` error means a question wasn't pre-answered; tell the user which one and ask how to resolve it.

## Step 10 — Move files to campaign subfolder

On success, move all files that were in the inbox root to the campaign subfolder:

```powershell
$dest = "D:\GoogleDrive\chapmand\My Drive\scrollcase\<campaign>\"
Move-Item "D:\GoogleDrive\chapmand\My Drive\scrollcase\<transcript>" $dest
# move any .ogg and fvtt-Actor-*.json files collected in Step 1
```

Only move the files identified in Step 1 — do not sweep the entire root in case another session was dropped in while this one was being processed.

## Step 11 — Hand off

List the files written by the script (it prints them) and confirm the files were moved. Then:

"Prep complete. When you're ready for the player recap, open a fresh conversation and run `/scrollcase-recap`."

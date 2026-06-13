Help the DM plan the *next* session for a scrollcase campaign. This is an open-ended planning conversation, not a mechanical extraction: read the latest debrief and campaign wiki, surface open threads and unused ideas, talk through what to run next, then write `<dm-dir>/sessions/YYYY-MM-DD-prep.md`.

`$ARGUMENTS` may contain a campaign name (`pandodnd`, `icewind-dale`, `log`) and/or a date (`YYYY-MM-DD`). If the date is omitted, default to the upcoming occurrence of this campaign's usual session weekday — see Step 1.

## Paths

| Thing | Path |
|---|---|
| pandodnd campaign dir | `C:\Users\decha\dev\hoshisabi.github.io\rpg\pandodnd` |
| icewind-dale campaign dir | `C:\Users\decha\dev\hoshisabi.github.io\rpg\icewind-dale` |
| log campaign dir | `C:\Users\decha\dev\hoshisabi.github.io\rpg\log` |
| pandodnd DM dir | `C:\Users\decha\dev\hoshisabi-dm\pandodnd` |
| icewind-dale DM dir | `C:\Users\decha\dev\hoshisabi-dm\icewind-dale` |
| log DM dir | `C:\Users\decha\dev\hoshisabi-dm\log` |

## Step 1 — Campaign and target date

If `$ARGUMENTS` specifies a campaign, use it. Otherwise use AskUserQuestion:

- question: "Which campaign are we planning for?"
- header: "Campaign"
- options: `pandodnd`, `icewind-dale`, `log`

If `$ARGUMENTS` specifies a date, use it and skip to Step 2.

Otherwise, derive the campaign's usual session weekday from its session history: look at the filenames in `<campaign-dir>/public/sessions/*.md` (`YYYY-MM-DD.md`), take the most recent few, and find the most common day of week (icewind-dale is the "FridayGame" per `al-dungeoncraft-reference.md` — expect Friday there). Then compute the next occurrence of that weekday on or after today:

```powershell
$today = Get-Date
$targetDow = [System.DayOfWeek]::Friday   # whichever weekday was derived above
$diff = ([int]$targetDow - [int]$today.DayOfWeek + 7) % 7
$nextDate = $today.AddDays($diff).ToString("yyyy-MM-dd")
```

Confirm with AskUserQuestion:

- question: "Plan for <Weekday>, <computed date>?"
- header: "Date"
- options:
  - "Yes, that date" (Recommended)
  - "A different date" — ask in chat (or use "Other" to type the date directly)

## Step 2 — Check for an existing draft

If `<dm-dir>/sessions/YYYY-MM-DD-prep.md` already exists for the target date, read it. Treat this run as continuing or revising that draft — say so before proceeding, and use it as the starting point in Step 4 rather than starting cold.

## Step 3 — Gather context

Read in parallel:

- The most recent `<dm-dir>/sessions/*-debrief.md` dated before the target date — especially **Preparation Guidance** (Pacing Advice, Likely Player Actions, Preparation Focus, Ideas & Suggestions) and **DM Tools**
- `<dm-dir>/threads.md` and `<dm-dir>/timeline.md`, if present — active threads and DM-only lore
- `<dm-dir>/characters/pcs/*.md` and `<dm-dir>/characters/npcs/*.md`, if present
- Campaign-specific wiki dirs if present (e.g. pandodnd's `factions/`, `locations/`, `npcs/`)
- The most recent existing `*-prep.md` (other than the target date's own, already read in Step 2) — as a structural/format reference
- `al-dungeoncraft-reference.md` or equivalent, if present — tier/APL and reward guidance
- `campaign.yaml`

## Step 4 — Surface ideas and talk it through

Pull out candidates: unresolved threads from `threads.md`, unused **DM Tools** from the last debrief, spotlight opportunities not yet paid off, anything flagged `[READY]` or similar, and any loose ends from **Unresolved Tensions**.

Present a short numbered list (4-8 items) of things that could go into the next session. Optionally use AskUserQuestion (multiSelect) for a quick first pass — "Which of these do you want to build into the next session?" — but treat that as a starting point, not the whole conversation. Continue talking it through: what's a must-do vs. optional, what the table's energy was like last time (per **Party Dynamics**/**Engagement Notes** in the debrief), whether anything from **Likely Player Actions** needs prep regardless of what else happens. Ask follow-ups. Push back gently if the plan skips an unresolved thread that seems to matter.

## Step 5 — Draft the prep document

Once the shape of the session is clear, draft `YYYY-MM-DD-prep.md`. Use the most recent existing `*-prep.md` as a loose structural reference (e.g. a Session Structure timing table, scene-by-scene breakdown, Main Encounter with stat notes, NPCs to Have Ready, Rewards, Notes) — but adapt sections to what this session actually needs. Not every session needs a combat encounter or a rewards table.

## Step 6 — Review and write

Show the draft. Use AskUserQuestion:

- question: "Ready to write this prep doc?"
- header: "Prep"
- options:
  - "Yes, write it" (Recommended)
  - "I have changes" — ask in chat what to fix, apply it, re-show the changed section(s), and ask this question again

Write the approved draft to `<dm-dir>/sessions/YYYY-MM-DD-prep.md`.

## Step 7 — Hand off

"Prep written to `<dm-dir>/sessions/YYYY-MM-DD-prep.md`. After the session: `/scrollcase-prep` to process the transcript, then `/scrollcase-debrief` for the write-up — its ideas feed back into the next round of this."

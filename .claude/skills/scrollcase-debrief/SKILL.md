---
name: scrollcase-debrief
description: >-
  Generate the DM-facing session debrief for a scrollcase campaign. Reads the context file,
  transcript, and campaign wiki, drafts a DM assistant report covering what happened and what it
  sets up, shows it for review, then writes it to `<dm-dir>/sessions/YYYY-MM-DD-debrief.md`.
---

Generate the DM-facing session debrief for a scrollcase campaign. Reads the context file, transcript, and campaign wiki, drafts a DM assistant report covering what happened and what it sets up, shows it for review, then writes it to `<dm-dir>/sessions/YYYY-MM-DD-debrief.md`.

These are ideas for *later* prep, not the next session's own battle plan — `<dm-dir>/sessions/YYYY-MM-DD-prep.md` (the forward-looking plan for whichever date the next session lands on) is a separate document and out of scope here.

`$ARGUMENTS` may contain a campaign name (`pandodnd`, `icewind-dale`, `log`) and/or a date (`YYYY-MM-DD`). If either is omitted, Step 1 asks for it — with a fallback to auto-detecting the most recent context file that has no debrief.

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

A session's context file is `<dm-dir>/sessions/YYYY-MM-DD-context.md`; a session is a candidate for debrief if it has **no** corresponding `<dm-dir>/sessions/YYYY-MM-DD-debrief.md`.

Resolve the **campaign** and **date**, asking for whatever `$ARGUMENTS` didn't supply:
- **Campaign** — if named in `$ARGUMENTS`, narrow to that campaign's DM dir; otherwise AskUserQuestion, header **Campaign**, options: `pandodnd`, `icewind-dale`, `log` (AskUserQuestion adds *Other* automatically).
- **Date** — if given in `$ARGUMENTS`, use it; otherwise AskUserQuestion, header **Date**, options: **Today** (the current date), **Yesterday** (current date − 1 day), **Enter a date** (`YYYY-MM-DD`). Resolve Today/Yesterday to a concrete `YYYY-MM-DD` using the current system date.

Then use `<dm-dir>/sessions/<date>-context.md` for the chosen campaign. If no matching context file exists, say so and fall back to the candidate set (context files with no debrief):
- If exactly one candidate remains, use it.
- If 2-4 candidates remain, use AskUserQuestion — question: "Which session should I debrief?", header: "Session", one option per candidate (e.g. "icewind-dale — 2026-06-12").
- If more than 4, list them and ask in chat which to process.
- If none, say so and stop.

## Step 2 — Read all the inputs

Read these in parallel:

- The context file (`<dm-dir>/sessions/YYYY-MM-DD-context.md`) — date, roster, DM name, transcript path
- The full transcript at the path listed in the context file
- `campaign.yaml` — `name`, `dm`
- `<dm-dir>/threads.md` and `<dm-dir>/timeline.md`, if present — ongoing campaign state, active/resolved threads, DM-only lore
- `<dm-dir>/characters/pcs/*.md` and `<dm-dir>/characters/npcs/*.md` — character backgrounds, arcs, notes
- `<dm-dir>/sessions/YYYY-MM-DD-prep.md`, if present — the plan going into this session, useful for noting what landed vs. what got deferred
- `<campaign-dir>/public/sessions/*.md` — count them (or read this session's own `title` frontmatter if its page already exists) to get the session number N

## Step 3 — Draft the debrief

Produce a report in this structure:

```
# DM Debrief — <Month D, YYYY>

Campaign: <campaign.yaml name> — Session <N>

---

## Session Summary

## Narrative Threads

## Unresolved Tensions

## Player & Character Analysis

### Party Dynamics

### Engagement Notes

### Spotlight Opportunities

## Preparation Guidance

### Pacing Advice

### Likely Player Actions

### Preparation Focus

### Ideas & Suggestions

## DM Tools
```

Section content follows `prompt_dm_assistant.md` (the DM Assistant Prompt template) — read it for per-section guidance on length, voice, and purpose. Study `<dm-dir>/sessions/2026-06-12-debrief.md` as a canonical formatting reference.

Ground everything in the transcript and wiki — do not invent plot details. Where `threads.md` has `[DM ONLY]` notes, it's fine to reason from them (this file stays under `dm/`, never published), but don't surface DM-only secrets in **Session Summary** beyond what the players actually learned.

If `<dm-dir>/sessions/YYYY-MM-DD-prep.md` exists for this date, use it to note what from the plan landed, what got deferred, and what diverged — this kind of comparison is what made the Session 8 debrief's **Unresolved Tensions** section useful.

## Step 4 — Show the draft and ask for review

Present the full draft. Then use AskUserQuestion:

- question: "Ready to write this debrief?"
- header: "Debrief"
- options:
  - "Yes, write it" (Recommended)
  - "I have corrections" — ask in chat what to fix, apply it, re-show only the changed section(s), and ask this question again

## Step 5 — Write the debrief

Write the approved draft to `<dm-dir>/sessions/YYYY-MM-DD-debrief.md`.

## Step 6 — Hand off

"Debrief written to `<dm-dir>/sessions/YYYY-MM-DD-debrief.md`. These are ideas for whenever you next sit down to prep — pull from **Preparation Guidance** and **DM Tools** when writing the next session's `-prep.md`."

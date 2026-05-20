# Scrollcase — backlog

## New session publish pipeline (future)

Mechanical steps should chain in a predictable order so recap writing stays human-paced, but nothing is missed when shipping a session to the site.

### 1. End-to-end checklist (write this up)

One ordered list spanning **miscprojects** and **hoshisabi.github.io**:

1. **Transcript / prep** — run `process_session.py` (and any campaign-specific steps) for dates, roster/context, prompts, etc.
2. **Recap page** — add or update `rpg/<campaign>/public/sessions/YYYY-MM-DD.md` (frontmatter, narrative, Player Highlights, Achievements).
3. **Wiki aliases** — add `also_known_as` on wiki YAML when recaps use shorthand names.
4. **Wiki links** — `uv run python scrollcase/link_session_entities.py <path-to/sessions> --write` (session file or directory under `public/sessions/`).
5. **Achievement art** — `generate_artwork.py` and/or `process_session.py --generate-images` as needed.
6. **Verify** — `bundle exec jekyll build` from the site repo root.

### 2. Discoverability

Expose the checklist where humans **and agents** see it first: pick **one** place of truth (e.g. expand this file, add a short section to `style_guide.md`, a workspace rule, or a pointer from `AGENTS.md`).

### 3. Orchestration (optional)

Add a thin wrapper script or `process_session.py` subcommands that run the deterministic steps in sequence without automating recap prose.

---

## Housekeeping

- **`link_session_entities.py`**: When narrative vs highlights or capitalization rules change, keep the module docstring aligned with the implementation so tooling docs stay truthful.

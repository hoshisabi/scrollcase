# scrollcase

Personal TTRPG session chronicle tool in this repo (`miscprojects/scrollcase`). It turns transcripts into markdown handoffs for AI-assisted recaps plus optional artwork generation. Campaign wikis and site content live separately (typically `hoshisabi.github.io`); scrollcase assumes a **`CAMPAIGN_DIR`** (or **`--campaign-dir`**) pointing at a campaign root with `campaign.yaml`, `dm/`, and `public/`.

## Campaigns using this toolchain

Icewind Dale, PandoDnD, Legends of Greyhawk, etc.—see **`README.md`** for the authoritative table (paths for `--campaign-dir`, workflow, `.env`). That file is source of truth; this stub only orients tooling.

## Components

| Script | Role |
|--------|------|
| `process_session.py` | Parses NoteCat / raw transcripts, Warhorn where configured, roster prompts, writes `dm/sessions/*` handoffs; **`--generate-images`** for achievement renders (same filenames as below) |
| `generate_artwork.py` | Imagen pipelines from YAML `image_prompt` (and legacy HTML comment prompts **only under** `public/sessions/`), optional **`--badge`** shield post-process |

Known patterns and file layout are summarized in **`README.md`**.

## Design principles

- Each stage is a checkpoint — transcript can be corrected before summary runs, summary before wiki updates
- Errors get caught at the source, not baked in silently
- Audio stays local; only text/images go to GitHub Pages where you publish them
- No third-party hosting dependency beyond APIs you explicitly wire (Gemini etc.)
- `dm/` vs `public/` is the hard privacy boundary — DM notes, full NPC details, raw transcripts, DM assistant prompts under `dm/`; player-facing recap and selectively published wiki pages under `public/`

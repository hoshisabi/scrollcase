Generate achievement badge images for a session page. Reads the image_prompt list from the session page frontmatter, shows the prompts for review and adjustment before spending API calls, then generates and optionally shield-crops the images.

`$ARGUMENTS` may contain a campaign name (`pandodnd`, `icewind-dale`, `log`), a date (`YYYY-MM-DD`), and/or `--badge` / `--no-badge` to pre-answer the shield-crop question. If omitted, find the most recent session page that has image prompts but no generated images yet.

## Paths

| Campaign | Campaign dir |
|---|---|
| pandodnd | `C:\Users\decha\dev\hoshisabi.github.io\rpg\pandodnd` |
| icewind-dale | `C:\Users\decha\dev\hoshisabi.github.io\rpg\icewind-dale` |
| log | `C:\Users\decha\dev\hoshisabi.github.io\rpg\log` |

| Thing | Path |
|---|---|
| scrollcase scripts | `C:\Users\decha\dev\scrollcase` |

## Step 1 — Find the session page

If `$ARGUMENTS` specifies a date, look for `public/sessions/YYYY-MM-DD.md` in the campaign dir. If a campaign is specified, use it. Otherwise check all three campaigns for the most recent session page that:
- Has an `image_prompt` list in its YAML frontmatter, AND
- Is missing at least one of the expected output images under `public/sessions/images/`

Expected image filenames: `YYYY-MM-DD.png` (single prompt) or `YYYY-MM-DD-1.png`, `YYYY-MM-DD-2.png`, … (multiple prompts).

Tell the user which session page you found before proceeding.

## Step 2 — Check for unresolved portraits

Before showing prompts, scan the session page for any `<img class="highlight-portrait">` tags whose `src` is the campaign default portrait (`/rpg/.../images/default-portrait.png`). For each one:

1. Find the character's page under `public/characters/`. If it has `dnd_beyond:`, query the DDB proxy (`POST /proxy/character` with `characterId` extracted from the URL, path `ddb.character.decorations.avatarUrl`) and update both the character page `image:` field and the session page `src` attribute.
2. If the character page exists but has no `dnd_beyond:`, or there is no character page, ask the user: "No portrait found for <Character>. Do you have a D&D Beyond character link or portrait URL?" Apply whatever they provide, or skip if they decline.

Once all portraits are resolved (or explicitly declined), proceed.

## Step 3 — Show the prompts for review

Read the `image_prompt` list from the session page frontmatter. Show them numbered:

```
Found 4 image prompts for 2026-05-20:

1. Bold vintage woodcut badge icon, clockwork robot reclining with eyes dimming...
2. Bold vintage woodcut badge icon, glowing green radioactive rock on a pedestal...
3. Bold vintage woodcut badge icon, enormous owl with many gleaming eyes diving...
4. Bold vintage woodcut badge icon, small gnome child surrounded by five tiny fire-breathing lizards...

Campaign prefix (prepended automatically):
  Bold vintage woodcut circular badge illustration, planar Pandemonium and tavern noir mood...

Any prompts to adjust before generating? (or "ok" to proceed)
```

If the user edits any prompts, update the session page frontmatter with the corrected text before running generation. Re-show the updated prompt(s) and confirm.

Also ask: "Shield-crop the badges? (yes / no — adds the heraldic border)" — skip this question if `--badge` or `--no-badge` was passed in `$ARGUMENTS`.

## Step 4 — Run generation

```powershell
cd C:\Users\decha\dev\scrollcase
uv run python generate_artwork.py `
  "<campaign-dir>\public\sessions\<YYYY-MM-DD>.md" `
  --campaign-dir "<campaign-dir>" `
  [--badge]
```

Add `--badge` if the user asked for shield cropping.

Stream the output. Each image is logged as it generates — show the filenames as they appear.

If the script errors (missing GOOGLE_KEY, network failure, etc.), report the message and stop.

## Step 5 — Offer to regenerate specific images

After generation completes, say:

"Generated <N> image(s) under `public/sessions/images/`. Review them and let me know if any need to be redone."

If the user wants to regenerate a specific image (e.g. "redo image 2"):

```powershell
uv run python generate_artwork.py `
  "<campaign-dir>\public\sessions\<YYYY-MM-DD>.md" `
  --campaign-dir "<campaign-dir>" `
  --image <N> --force [--badge]
```

To adjust a prompt and regenerate: edit the session page frontmatter first, then run with `--image N --force`.

To apply badge cropping to already-generated images without regenerating:

```powershell
uv run python generate_artwork.py `
  "<campaign-dir>\public\sessions\<YYYY-MM-DD>.md" `
  --campaign-dir "<campaign-dir>" `
  --badge-only
```

## Step 6 — Hand off

"Images are in `public/sessions/images/`. When you're happy with them:

```powershell
cd C:\Users\decha\dev\hoshisabi.github.io
git add rpg/<campaign>/
git commit -m 'session YYYY-MM-DD'
git push
```"

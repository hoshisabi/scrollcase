---
name: scrollcase-artgen
description: >-
  Generate achievement badge images for a session page. Reads the image_prompt list from the
  session page frontmatter, shows the prompts for review and adjustment before spending API
  calls, then generates and optionally shield-crops the images.
---

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

1. Find the character's page under `public/characters/`. If it has `dnd_beyond:`, query the DDB proxy (`http://blueglow:3000`, falling back to `http://localhost:3000`; `POST /proxy/character` with `characterId` extracted from the URL, path `ddb.character.decorations.avatarUrl`). **Don't hotlink that URL.** Download and convert it to `public/images/portraits/<slug>.webp` exactly as step 5 of the portrait rule in `/scrollcase-recap` says (WebP, 512px cap), then point both the character page `image:` field and the session page `src` attribute at the local `/rpg/<campaign>/public/images/portraits/<slug>.webp`.
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
```

Then use AskUserQuestion:

- question: "Ready to generate these prompts?"
- header: "Prompts"
- options:
  - "Generate as shown" (Recommended)
  - "Edit one or more first" — ask in chat which prompt(s) to change and how, update the session page frontmatter with the corrected text, re-show the updated prompt(s), and ask this question again

If `--badge` or `--no-badge` was passed in `$ARGUMENTS`, use that and skip the next question. Otherwise use AskUserQuestion:

- question: "Shield-crop the badges?"
- header: "Badge crop"
- options:
  - "Yes — add heraldic border"
  - "No — plain image"

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

## Step 5 — Show the images and offer to regenerate

After generation completes, say "Generated <N> image(s) under `public/sessions/images/`." and show them so the user doesn't have to find them in the folder:

1. Read each generated image with the Read tool, so you can see it too. Point out anything visibly off (garbled text, extra limbs, a badge border cut through the subject) — briefly, without grading the art.
2. Display them in the window, depending on the host:
   - **Claude desktop app** (`$env:CLAUDE_CODE_ENTRYPOINT` is `claude-desktop`): open each image in the Files pane with `mcp__ccd_view__show_pane` (`pane: "file"`, `path: <image>`). That pane only opens files inside the session's folders or the scratchpad, so if the image path is refused, copy the images into `<scratchpad>\artgen\` first (`Copy-Item … -Force`) and open the copies. Markdown image embeds with local paths don't render in the desktop app, and `SendUserFile` shows only a file card.
   - **T3 Code**: embed each image as markdown, numbered to match the prompts. Two T3 quirks:
     - It caches images by path, so after a regenerate the original path still shows the old image (a `?v=` query string doesn't help). Copy each image to a fresh name first and embed the copy:

       ```powershell
       $dir = Join-Path $env:TEMP 'scrollcase-preview'; New-Item -ItemType Directory -Force $dir | Out-Null
       $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
       Copy-Item <image> (Join-Path $dir "<image-stem>-$stamp.png")
       ```

       ```markdown
       **1.** ![2026-05-20-1](C:/Users/decha/AppData/Local/Temp/scrollcase-preview/2026-05-20-1-20260520-213004.png)
       ```

     - It only renders images in the final message of a turn, not in text written before a tool call. So put the images at the end of your reply and ask the review question below in plain chat ("All good, regenerate N, or change prompt N?"), ending the turn. Don't use AskUserQuestion for it.
   - **Terminal** (`$env:CLAUDE_CODE_ENTRYPOINT` is `cli`, which can't render images): open each in the default viewer with `Invoke-Item <path>`.

Show only the images generated in this run. After a regenerate, show just the replaced image(s) the same way.

Then ask (AskUserQuestion, except in T3 Code — see above):

- question: "How do the generated images look?"
- header: "Review"
- options:
  - "All good" (Recommended) — proceed to Step 6
  - "Regenerate one or more" — ask in chat which image number(s), then run with `--image <N> --force [--badge]` below
  - "Edit a prompt and regenerate" — ask in chat which prompt and the new text, update the session page frontmatter, then run with `--image <N> --force [--badge]` below

To regenerate a specific image:

```powershell
uv run python generate_artwork.py `
  "<campaign-dir>\public\sessions\<YYYY-MM-DD>.md" `
  --campaign-dir "<campaign-dir>" `
  --image <N> --force [--badge]
```

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

## Step 7 — Clean up preview copies

Only if Step 5 made preview copies (T3 Code). List them with their total size:

```powershell
Get-ChildItem (Join-Path $env:TEMP 'scrollcase-preview') -Filter '<YYYY-MM-DD>*.png'
```

Then use AskUserQuestion:

- question: "Delete the <N> preview copies in %TEMP%\scrollcase-preview (<size>)?"
- header: "Cleanup"
- options:
  - "Yes — delete them" (Recommended) — `Remove-Item` exactly the files listed, nothing else in the folder
  - "No — keep them"

The originals under `public/sessions/images/` are untouched either way.

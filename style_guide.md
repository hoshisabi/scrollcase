# Scrollcase Campaign Style Guide — Icewind Dale

## Visual Style

**Reference:** 1930s–40s pulp adventure paperback covers. Doc Savage, early Robert E. Howard illustrations, adventure magazines of the era.

**Core characteristics:**
- Bold, confident linework
- Limited color palette — 2 to 3 dominant colors per image
- Flat or minimal backgrounds; negative space is a tool, not a failure
- Dramatic poses and lighting; no ambiguity about mood
- Snow and ice rendered as stark white negative space, not detailed texture
- Cold palette as the default: deep blues, slate grays, icy whites
- Warm amber or orange reserved for firelight, torchlight, magic — makes it pop against the cold

**What to avoid:**
- Photorealistic rendering
- Busy, detailed backgrounds
- Soft gradients and painterly blending (this is pulp, not fine art)
- Modern fantasy art conventions (lens flare, particle effects, etc.)

## Standard Prompt Prefix

The campaign-wide style prefix lives in `campaign.yaml` as `image_prompt_prefix`. The generator prepends it automatically to every image; you never repeat it in session or character files.

Current value:
```
1930s pulp adventure paperback illustration style, bold linework, limited color palette of deep blues and slate grays with stark white snow, flat simplified background, dramatic lighting, arctic Icewind Dale setting with snow and ice always present, absolutely no text, no letters, no words, no labels anywhere in the image
```

A session file can add a per-session refinement via `image_prompt_prefix` in its own frontmatter (appended after the campaign prefix). Leave it out if the campaign default is sufficient.

Note: suppress all text in generated images. Title banners and labels will be added via PIL in post-processing so they are consistent and correct.

## Character Prompt Templates

### PCs
```
[PREFIX] [character description], D&D adventurer portrait
```

### NPCs
```
[PREFIX] [character description], D&D character portrait
```

### Achievement Icons
```
[PREFIX] small circular badge icon, [achievement description], bold simple shapes
```

## Embedding Achievements in Session Pages

Image prompts live in the frontmatter as a YAML list. Each item is the scene-specific part only — the campaign prefix is added automatically at generation time.

```yaml
---
image_prompt:
  - warrior in the snow, bold simple shapes
  - party fleeing through a blizzard, bold simple shapes
---
```

The generator (`generate_artwork.py`, or `process_session.py --generate-images DATE`) names images `YYYY-MM-DD-1.png`, `YYYY-MM-DD-2.png`, etc., matching the list order (single prompt ⇒ `YYYY-MM-DD.png`). Both scripts share the same pipeline.

Optional shield crop for achievement PNGs matches the flex layout icons:

```
uv run python generate_artwork.py public/sessions/YYYY-MM-DD.md --badge
```

Use `--badge-only` on markdown that already has images to reshape existing files without regenerating via Imagen. Tunables: `--badge-size`, `--badge-width`, `--badge-color`.

If this session needs style details beyond the campaign default, add `image_prompt_prefix` to the frontmatter:

```yaml
image_prompt_prefix: "underground cavern, warm firelight against cold stone"
```

Each achievement block in the page body:

```html
<div class="achievement">
<img class="achievement-badge" src="images/YYYY-MM-DD-N.png" alt="[achievement title]">
<p><strong>[Achievement Title]</strong> — [1-2 sentence description of the moment]</p>
</div>
```

Rules:
- Wrap each achievement in `<div class="achievement">` — this creates a flex row (icon left, text right, text never wraps under the icon).
- Use `<p><strong>...</strong></p>` for the description, not markdown bold — the div is an HTML block so markdown inside it won't render.
- Use the achievement title as `alt` text, not the full prompt.
- No `clear:both` div needed after the last achievement — the flex layout doesn't use floats.

To regenerate only one image (e.g. image 3):

```
uv run python generate_artwork.py public/sessions/YYYY-MM-DD.md --image 3 --force
```

**Legacy prompts:** Older pages may omit frontmatter prompts and instead use HTML comments embedded in the body (`<!-- image_prompt: … -->`). The tooling still discovers those comments **only under** `public/sessions/`; new pages should prefer YAML `image_prompt`.

## Player Highlights (portraits)

Wrap each highlight like achievements: **flex row** (portrait left, text right), **no** shield mask — rectangular portrait with the same border radius as achievement icons.

```html
<div class="highlight">
<img class="highlight-portrait" src="/rpg/your-campaign/public/characters/images/berg.png" alt="Berg portrait">
<p><strong>Berg</strong> — [2–4 sentences of recap].</p>
</div>
```

**`src`**: copy the URL from that character’s **`image`** field in `public/characters/<slug>.md` (or `public/npcs/...` if the highlight is about an NPC). Paths are usually site-root absolute (`/rpg/...`) or a full **D&D Beyond** avatar URL for drop-in campaigns.

**Markup rules** (same spirit as achievements):

- One `<div class="highlight">` per bullet; portrait + single `<p>...</p>`.
- Put the whole highlight in `<p><strong>Name</strong> — …</p>` — raw markdown bold won’t parse inside the surrounding HTML block the same way once you mix tags; using `<strong>` keeps it reliable.
- Use a short `alt` (e.g. `Sparrow portrait`).

## Faction Notes

- **Thunlakalaga / Reghed nomads:** Large, powerful humanoids in heavy furs and hides. Practical warrior aesthetics — nothing decorative that doesn't serve a purpose. Think Viking meets arctic survival gear, pulp style.
- **The Owlbear (Frostclaw):** White and crimson, 14 feet tall. Should feel like a pulp monster — iconic silhouette, not photorealistic creature design.
- **Netherese ruins:** Cold stone, geometric patterns, deep shadows. Occasional magical glow should be amber or pale blue.

## Color Palette

| Use | Colors |
|-----|--------|
| Background / sky | Deep navy, slate gray |
| Snow / ice | Stark white, pale blue-white |
| Skin / warmth | Muted amber, weathered tan |
| Accent / fire / magic | Warm amber, burnt orange |
| Shadow | Near-black with blue undertone |

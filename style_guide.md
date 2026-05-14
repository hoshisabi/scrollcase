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

Use this prefix for all campaign images:

```
1930s pulp adventure paperback illustration style, bold linework, limited color palette of deep blues and slate grays with stark white snow, flat simplified background, dramatic lighting, arctic Icewind Dale setting with snow and ice always present, absolutely no text, no letters, no words, no labels anywhere in the image —
```

Then append the character/subject description.

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

Each achievement block follows this pattern:

```html
<!-- image_prompt: [full image generation prompt] -->
<img class="achievement-badge" src="images/YYYY-MM-DD-achievement-N.png" alt="[achievement title]">

**[Achievement Title]** — [1-2 sentence description of the moment]
```

Rules:
- The `<!-- image_prompt: ... -->` comment is parsed by `process_session.py --generate-images` — keep it on its own line, one per achievement, in order.
- Use `class="achievement-badge"` (defined in `assets/css/style.css`) — floats the badge left at 72px with the description wrapping right.
- Use the achievement title as `alt` text, not the full prompt.
- After the last achievement block, add `<div style="clear:both"></div>` to prevent float bleed.

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

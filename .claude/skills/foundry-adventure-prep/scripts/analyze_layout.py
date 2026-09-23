#!/usr/bin/env python3
r"""Decide which pages of an adventure PDF actually need the vision step.

Reading every page as an image is the expensive fallback, not the default. Most
of an adventure is linear prose with a real text layer that PyMuPDF extracts far
more cheaply and accurately than transcribing from a picture. Vision is only
*needed* for the layout-dependent parts:

    * the cover        -- usually a flattened image with no text layer
    * the battle map   -- read the scale bar / grid
    * modifier sidebars sitting beside a stat block (e.g. the planar "Petitioner"
      box), where the grey box changes an adjacent creature and flat text loses
      which creature it points at

This script scans the PDF with text + geometry (no model calls) and prints a
manifest: per page, its role(s), the shaded callout boxes it found (with body
text and the nearest heading, for attribution), and a short VISION list naming
the pages that still want an eyeball and why. Feed that manifest to the prep
step and vision-read only the flagged pages.

The shaded boxes in this publisher's PDFs are drawn as a *stack* of thin grey
per-line strips rather than one tall rectangle, so we collect grey strips and
cluster vertically-contiguous same-column strips into a box. Small-caps headings
render their first letter as a separate oversized span ("A DJUSTING THE S CENE"),
so text is normalised before matching.

Usage:
    python analyze_layout.py <pdf> [<pdf> ...]        # human-readable manifest
    python analyze_layout.py --json <pdf>             # machine-readable manifest

If the geometry heuristic finds no boxes on a text-heavy page (a different
publisher, image-based shading, ...), that is a *safe* miss: nothing is flagged
falsely; at worst a sidebar is left for the normal text pass to surface, exactly
as before this script existed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

try:
    import pymupdf  # PyMuPDF >= 1.24
except ImportError:  # older installs only expose `fitz`
    import fitz as pymupdf


# ---- page-role classification (cheap, text-only) --------------------------
ABILITY_HDR = re.compile(r"STR\s+DEX\s+CON\s+INT\s+WIS\s+CHA", re.I)
CR_LINE     = re.compile(r"\bCR\s+[\d/]+", re.I)
AC_HP       = re.compile(r"\bAC\b.*\bHP\b", re.I | re.S)
RARITY      = re.compile(r"\b(Wondrous Item|Requires Attunement|Scroll,|Rod,|Wand,|Ring,|Staff,)\b", re.I)
GOLD_TABLE  = re.compile(r"Gold Value|\bMaximum\b\s*[\d,]+\s*gp", re.I)
MAP_HINT    = re.compile(r"\bMap of\b|Appendix\s*1\b|\bft\.\b", re.I)

# an NPC callout box's second line: alignment + race + pronouns, e.g.
# "NG human (she/her) precocious child"
NPC_LINE = re.compile(r"\b(?:L|N|C)?[GNE]\s+[A-Za-z-]+\s+\([^)]*/[^)]*\)", re.I)

# generic callout / modifier headers that recur across the series
MODIFIER_HDRS   = ("PETITIONER",)                    # modifies an adjacent stat block
BOILERPLATE_HDRS = (                                 # DM-tips boilerplate; drop
    "SAFETY TOOLS", "DETERMINING PARTY STRENGTH",
    "NEW TO D&D ADVENTURERS LEAGUE", "ADJUSTING THIS ADVENTURE",
    "PREPARING THE ADVENTURE",
)


def normalise(text: str) -> str:
    """Collapse the small-caps drop-letter artifact: a lone capital followed by
    a space and another capital ("A DJUSTING", "S CENE") rejoins, while genuine
    word boundaries ("THE SCENE") are left alone."""
    text = re.sub(r"(?<![A-Za-z])([A-Z]) (?=[A-Z])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def grey_boxes(page):
    """Shaded callout boxes, reconstructed from stacked grey strips."""
    strips = []
    for d in page.get_drawings():
        fill = d.get("fill")
        if not fill or len(fill) < 3:
            continue
        r, g, b = fill[:3]
        if abs(r - g) < 0.06 and abs(g - b) < 0.06 and 0.45 < r < 0.97:
            rect = d["rect"]
            if rect.width > 80:                      # column-wide, not a tick
                strips.append(pymupdf.Rect(rect))

    strips.sort(key=lambda r: (round(r.x0 / 10), r.y0))
    boxes = []
    for s in strips:
        placed = False
        for i, m in enumerate(boxes):
            same_col = abs(s.x0 - m.x0) < 12 and abs(s.x1 - m.x1) < 12
            contiguous = -3 <= (s.y0 - m.y1) <= 6
            if same_col and contiguous:
                boxes[i] = m | s                      # reassign; |= would only rebind
                placed = True
                break
        if not placed:
            boxes.append(pymupdf.Rect(s))
    return [m for m in boxes if m.height > 22]        # a real box spans >1 line


def text_blocks(page):
    return [b for b in page.get_text("dict")["blocks"] if b.get("type") == 0]


def block_text(b):
    return normalise(" ".join(
        s["text"] for l in b["lines"] for s in l["spans"]
    ).strip())


def block_maxsize(b):
    return max((s["size"] for l in b["lines"] for s in l["spans"]), default=0)


def nearest_heading(page, box, blocks):
    """The text block just above the box in the same column -- the section the
    box sits beside, used to attribute a modifier sidebar to its stat block."""
    cand = []
    for b in blocks:
        r = pymupdf.Rect(b["bbox"])
        if abs(r.x0 - box.x0) < 120 and r.y1 <= box.y0 + 4:
            cand.append((r.y1, block_maxsize(b), block_text(b)))
    if not cand:
        return None
    cand.sort(key=lambda t: (-t[0], -t[1]))
    return cand[0][2][:70]


def label_box(body: str, on_statblock_page: bool):
    """Return (label, needs_vision, reason)."""
    head = body[:60].upper()
    if any(h in head for h in BOILERPLATE_HDRS):
        return "boilerplate", False, ""
    if any(h in head for h in MODIFIER_HDRS) or "PETITIONER" in body[:120].upper():
        return "modifier", True, "modifier box -- confirm which stat block it changes"
    if on_statblock_page:
        return "modifier?", True, "box on a stat-block page -- confirm attribution"
    if NPC_LINE.search(body):
        return "npc", False, ""
    return "callout", False, ""


# creatures named after an Add/Remove verb in an "Adjusting the Scene" box,
# e.g. "Add two modron monodrones", "Remove the mage and three toughs"
ADJUST_CREATURE = re.compile(
    r"(?:a|an|the|one|two|three|four|five|six|\d+)\s+"
    r"([a-z][a-z ]+?)(?=\s+and\b|[.,;:]|$)", re.I)


# nouns that follow a count word but are never a creature to prep a block for
NON_CREATURE = {
    "hit point", "temporary hit point", "gp", "gold", "foot", "feet", "round",
    "minute", "hour", "day", "level", "die", "dice", "damage", "suggestion",
    "attack", "target", "point", "creature",
}
# stat-adjustment phrasing ("The retriever has 21 AC and 300 hit points") that
# isn't an add/remove of a creature
STAT_ADJ = re.compile(r"\bhas\b|\bAC\b|\bhit point", re.I)


def singular(name: str) -> str:
    """Lowercase and strip a trailing plural 's' from every word (so
    'swarms of spiders' and 'swarm of spider' collapse to one form)."""
    words = " ".join(name.lower().split()).split()
    words = [w[:-1] if (len(w) > 3 and w.endswith("s")) else w for w in words]
    return " ".join(words)


def adjust_creatures(body: str):
    """Creature names referenced in an Adjusting-the-Scene box (singularised).
    Only Add/Remove-of-a-creature clauses count; stat tweaks and unit nouns
    (hit points, AC, gp, ...) are filtered out."""
    found = set()
    for m in re.finditer(r"\b(?:Add|Remove)\b([^.;]*)", body, re.I):
        clause = m.group(1)
        if STAT_ADJ.search(clause):          # "...has 300 hit points" -> not a creature add
            continue
        for c in ADJUST_CREATURE.finditer(clause):
            s = singular(c.group(1))
            if s and s not in NON_CREATURE and \
               not re.search(r"\b(weak|strong|average|suggestion|scene)\b", s):
                found.add(s)
    return found


# player-facing handout signals
APPENDIX_HDR = re.compile(r"APPENDIX\s+(\d+)\s*[:.]?\s*([A-Z0-9][A-Z0-9 '&:/-]+?)(?=[A-Z][a-z]|$)")
HANDOUT_REF  = re.compile(r"handout[^.]{0,40}?Appendix\s+(\d+)|Appendix\s+(\d+)[^.]{0,20}?handout", re.I)
GIVE_PLAYERS = re.compile(
    r"give (?:your |the |it to )?players|give (?:one|a copy)[^.]{0,30}players"
    r"|print[^.]{0,30}cop|show[^.]{0,20}players|player handout|hand (?:this |it )?to", re.I)
# appendix titles that are DM-facing, never a player handout
DM_FACING = re.compile(r"DUNGEON MASTER|\bDM\b|TIPS|CREDITS|STATISTICS|STAT BLOCK", re.I)

# a random-effect table ("Roll a d6 ...: 1-2. ... 3-4. ...") -> Foundry Rolltable candidate.
# Require the die roll AND >=2 numbered outcome ranges so ordinary "roll a d20 check" misses.
ROLL_TRIGGER = re.compile(r"\broll\s+(?:a\s+)?\d*d(?:4|6|8|10|12|20|100)\b", re.I)
ROLL_OUTCOME = re.compile(r"\b\d+\s*[-–]\s*\d+\.\s")


def page_roles(text, imgs, page_index):
    roles = []
    if ABILITY_HDR.search(text) or (AC_HP.search(text) and CR_LINE.search(text)):
        roles.append("statblock")
    if RARITY.search(text):
        roles.append("reward")
    if GOLD_TABLE.search(text):
        roles.append("gold")
    if page_index == 0 and imgs and len(text.strip()) < 400:
        roles.append("cover")
    if imgs and MAP_HINT.search(text) and len(text.strip()) < 600:
        roles.append("map")
    return roles


def analyze(path):
    doc = pymupdf.open(path)
    pages = []
    statblock_text = []            # concatenated text of every stat-block page
    adjust_refs = {}               # creature -> first page it's referenced from
    doc_text_parts = []            # whole-doc text, for cross-references
    appendices = {}                # num -> {title, page, role, textlen, give}
    rolltables = []                # pages with a "roll a dX" random-effect table
    for i, page in enumerate(doc):
        raw = page.get_text()
        text = normalise(raw)
        doc_text_parts.append(text)
        blocks = text_blocks(page)
        imgs = page.get_images()
        roles = page_roles(text, imgs, i)
        on_sb = "statblock" in roles
        if on_sb:
            statblock_text.append(text.lower())

        if ROLL_TRIGGER.search(text) and len(ROLL_OUTCOME.findall(text)) >= 2:
            m = ROLL_TRIGGER.search(text)
            rolltables.append({"page": i + 1,
                               "snippet": text[m.start():m.start() + 90].strip()})

        for am in APPENDIX_HDR.finditer(text):
            num, title = am.group(1), am.group(2).strip()
            appendices.setdefault(num, {
                "num": num, "title": title, "page": i + 1,
                "role": ("map" if "map" in roles else
                         "statblock" if on_sb else "text"),
                "textlen": len(text), "give": bool(GIVE_PLAYERS.search(text)),
            })

        sidebars = []
        for box in grey_boxes(page):
            inside = [block_text(b) for b in blocks
                      if pymupdf.Rect(b["bbox"]).intersects(box)]
            body = " ".join(inside).strip()
            if len(body) < 15:
                continue
            label, needs_vision, reason = label_box(body, on_sb)
            if "ADJUSTING THE SCENE" in body[:60].upper():
                for c in adjust_creatures(body):
                    adjust_refs.setdefault(c, i + 1)
            sidebars.append({
                "label": label,
                "near": nearest_heading(page, box, blocks),
                "text": body[:200],
                "needs_vision": needs_vision,
                "reason": reason,
            })

        vision = []
        if "cover" in roles:
            vision.append("cover: no/low text layer")
        if "map" in roles:
            vision.append("map: read scale bar / grid")
        for s in sidebars:
            if s["needs_vision"]:
                vision.append(f"{s['label']} sidebar: {s['reason']}")

        if roles or sidebars:
            pages.append({
                "page": i + 1,
                "roles": roles,
                "images": len(imgs),
                "sidebars": sidebars,
                "vision": vision,
            })

    # QA: creatures named in "Adjusting the Scene" boxes that have no stat block
    # in the appendix -- a common author slip worth catching before we run it.
    sb_all = " ".join(statblock_text)
    missing = []
    for creature, pg in sorted(adjust_refs.items(), key=lambda kv: kv[1]):
        forms = {creature, creature + "s"}
        if not any(f in sb_all for f in forms):
            missing.append({"creature": creature, "referenced_page": pg})
    # Handout candidates: appendices that look player-facing. An appendix is
    # flagged when the body refers to it as a "handout", or its own page has
    # give-to-players / print-copies language, or it's a substantial text/table
    # appendix that isn't DM-facing or already handled as a map/stat block.
    doc_text = " ".join(doc_text_parts)
    handout_ref_nums = {n for pair in HANDOUT_REF.findall(doc_text)
                        for n in pair if n}
    handouts = []
    for num, a in sorted(appendices.items(), key=lambda kv: int(kv[0])):
        if a["role"] in ("map", "statblock") or DM_FACING.search(a["title"]):
            continue
        reasons = []
        if num in handout_ref_nums:
            reasons.append('referred to as a "handout" in the text')
        if a["give"]:
            reasons.append("give-to-players / print-copies language on the page")
        if not reasons and a["textlen"] > 300:
            reasons.append("substantial text/table appendix — possibly player-facing")
        if reasons:
            handouts.append({**a, "reasons": reasons})

    return {
        "pdf": path,
        "page_count": doc.page_count,
        "pages": pages,
        "adjust_creatures": sorted(adjust_refs),
        "missing_statblocks": missing,
        "handouts": handouts,
        "rolltables": rolltables,
    }


def print_human(manifest):
    print(f"\n===== {manifest['pdf']}  ({manifest['page_count']} pages) =====")
    vision_pages = []
    for p in manifest["pages"]:
        keep = [s for s in p["sidebars"] if s["label"] != "boilerplate"]
        if not (p["roles"] or keep):
            continue
        print(f"\n p{p['page']:>2}: roles={p['roles'] or '-'}  "
              f"imgs={p['images']}  boxes={len(keep)}")
        for s in keep:
            print(f"       [{s['label']}] near<{s['near']}>: {s['text'][:72]!r}")
        if p["vision"]:
            vision_pages.append(p["page"])
            print(f"       -> VISION: {'; '.join(p['vision'])}")
    print(f"\n  Vision needed on {len(vision_pages)} page(s): "
          f"{vision_pages or 'none'}  (out of {manifest['page_count']})")

    if manifest["adjust_creatures"]:
        print(f"\n  Adjusting-the-Scene creatures: "
              f"{', '.join(manifest['adjust_creatures'])}")
    miss = manifest["missing_statblocks"]
    if miss:
        print("  ** QA: named in Adjusting the Scene, no exact-name stat block found -- VERIFY: **")
        for m in miss:
            print(f"       - {m['creature']}  (referenced p{m['referenced_page']}) "
                  f"-- reflavoured block, MM lookup, or a genuine omission we must prep?")
    elif manifest["adjust_creatures"]:
        print("  QA: all Adjusting-the-Scene creatures have stat blocks. OK.")

    if manifest["handouts"]:
        print("\n  ** Possible player handouts -- ASK Dan whether to make each one: **")
        for h in manifest["handouts"]:
            print(f"       - Appendix {h['num']}: {h['title']}  (p{h['page']})")
            print(f"           why: {'; '.join(h['reasons'])}")
    if manifest["rolltables"]:
        print("\n  Random-effect tables (Foundry Rolltable candidates -- capture in Prep Doc):")
        for r in manifest["rolltables"]:
            print(f"       - p{r['page']}: {r['snippet']!r}")
    print()


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdfs", nargs="+", help="Adventure PDF(s) to analyze")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = ap.parse_args()

    out = [analyze(p) for p in args.pdfs]
    if args.json:
        json.dump(out if len(out) > 1 else out[0], sys.stdout, indent=2)
        print()
    else:
        for m in out:
            print_human(m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""First-occurrence wiki links for session recap markdown.

Reads ``title`` plus optional ``also_known_as`` from ``public/{characters,npcs,locations}/``.
Replaces ONLY the FIRST mention per entity slug within narrative + highlights
(everything before ``## Achievements``), excluding a ``## Rewards`` block when it
appears above ``## Achievements`` (currently unused).

Matching is **case-insensitive**, but the recap's original casing is preserved in
links. Labels are matched longest-first via ``collect_entity_jobs``.

Standalone ``<img ...>`` lines are emitted unchanged so ``alt``/``src`` are never
altered; bracket-balanced ``[text](url)`` spans (even with nested brackets) are
skipped so existing links stay intact.

Transforms:
  - ``**Name**`` -> ``[**Name**](../category/slug)``
  - ``<strong>Name</strong>`` -> ``<strong><a href="../category/slug">Name</a></strong>``
  - Plain ``Name`` -> ``[**Name**](...)``, including possessives ``River's``

Usage:
    uv run python link_session_entities.py SESSION.md
    uv run python link_session_entities.py SESSION.md --write
    uv run python link_session_entities.py PUBLIC/sessions/ --write   # all *.md
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

import yaml

ENTITY_DIRS = ("characters", "npcs", "locations")

_IMG_TAG_INLINE_RE = re.compile(r"(<img[^>\n]+>)", re.IGNORECASE)
_EXISTING_MD_LINK_STEMS = re.compile(
    r"\[\*\*[^*]+\*\*\]\(\.\./(?:characters|npcs|locations)/([^)]+)\)"
)
_EXISTING_HREF_STEMS = re.compile(r'href="\.\./(?:characters|npcs|locations)/([^"#]+)"')


def _seed_existing_wiki_links(middle: str, linked: set[str]) -> None:
    for rx in (_EXISTING_MD_LINK_STEMS, _EXISTING_HREF_STEMS):
        for m in rx.finditer(middle):
            raw = m.group(1).strip()
            stem = raw.split("/")[-1].removesuffix(".md")
            linked.add(stem)


def _read_frontmatter_dict(path: pathlib.Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    try:
        end = text.index("---", 3)
    except ValueError:
        return None
    return yaml.safe_load(text[3:end]) or None


def collect_entity_jobs(public_dir: pathlib.Path) -> list[tuple[str, str, str]]:
    """Return list of (label, stem, category). Labels sorted longest-first globally."""
    by_stem_cat: dict[tuple[str, str], list[str]] = {}

    for category in ENTITY_DIRS:
        sub = public_dir / category
        if not sub.is_dir():
            continue
        for md in sorted(sub.glob("*.md")):
            fm = _read_frontmatter_dict(md)
            if not fm or not fm.get("title"):
                continue
            stem = md.stem
            labels = [str(fm["title"]).strip()]
            for a in fm.get("also_known_as") or []:
                s = str(a).strip()
                if s and s not in labels:
                    labels.append(s)
            by_stem_cat[(stem, category)] = labels

    rows: list[tuple[str, str, str]] = []
    for (stem, category), labs in by_stem_cat.items():
        for lab in labs:
            rows.append((lab, stem, category))
    rows.sort(key=lambda x: -len(x[0]))
    return rows


def _split_middle_for_linking(md_text: str) -> tuple[str, str, str]:
    """Return head (frontmatter through closing delimiter), middle, tail (achievements+)."""
    if not md_text.startswith("---"):
        return "", md_text, ""
    try:
        end_fm = md_text.index("---", 3)
    except ValueError:
        return "", md_text, ""
    head = md_text[: end_fm + 3]
    body = md_text[end_fm + 3 :]

    ach_parts = body.split("\n## Achievements", 1)
    before_ach = ach_parts[0]
    ach_tail = ("\n## Achievements" + ach_parts[1]) if len(ach_parts) > 1 else ""

    rew_parts = before_ach.split("\n## Rewards", 1)
    middle = rew_parts[0]
    rew_tail = ("\n## Rewards" + rew_parts[1]) if len(rew_parts) > 1 else ""

    return head, middle, ach_tail + rew_tail


def _is_wordish(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _link_text_close_index(s: str, open_bracket: int) -> int:
    """Return index one past the `]` that closes `[` at open_bracket, or -1."""
    if open_bracket >= len(s) or s[open_bracket] != "[":
        return -1
    depth = 1
    i = open_bracket + 1
    while i < len(s) and depth:
        if s[i] == "[":
            depth += 1
        elif s[i] == "]":
            depth -= 1
        i += 1
    if depth:
        return -1
    return i


def _markdown_inline_link_len(s: str, pos: int) -> int:
    """Length of ``[text](url)`` or ``![text](url)`` at pos; 0 if not a link."""
    if pos >= len(s):
        return 0
    open_bracket = pos
    if s.startswith("![", pos):
        open_bracket = pos + 1
    elif not s.startswith("[", pos):
        return 0
    after_text = _link_text_close_index(s, open_bracket)
    if after_text < 0 or after_text >= len(s) or s[after_text] != "(":
        return 0
    rp = s.find(")", after_text + 1)
    if rp < 0:
        return 0
    return rp - pos + 1


def _consume_skippable_prefix(segment: str, pos: int, buf: list[str]) -> int:
    """Append skipped span to buf; return chars consumed after pos."""
    z = segment[pos:]
    if not z:
        return 0

    if z.startswith("```"):
        end_fence = z.find("\n```", 3)
        if end_fence < 0:
            buf.append(z)
            return len(z)
        buf.append(z[: end_fence + 4])
        return end_fence + 4

    ml = _markdown_inline_link_len(segment, pos)
    if ml > 0:
        buf.append(segment[pos : pos + ml])
        return ml

    zn = z.lower()
    if zn.startswith("<a"):
        gt = z.find(">")
        if gt > 0:
            close = zn.find("</a>", gt)
            if close > 0:
                buf.append(z[: close + 4])
                return close + 4

    return 0


def _link_text_segment(
    segment: str, jobs_sorted: list[tuple[str, str, str]], linked_stems: set[str]
) -> str:
    buf: list[str] = []
    pos = 0

    while pos < len(segment):
        skipped = _consume_skippable_prefix(segment, pos, buf)
        if skipped:
            pos += skipped
            continue

        matched = False
        zone = segment[pos:]
        zlo = zone.lower()
        blob_lo = "<strong>"
        blob_hi = "</strong>"

        for label, stem, cat in jobs_sorted:
            if stem in linked_stems:
                continue
            href = f"../{cat}/{stem}"
            lf = label.casefold()

            if zlo.startswith(blob_lo):
                gt = zone.find(">", 0)
                clo = zlo.find(blob_hi, gt + 1)
                if gt != -1 and clo != -1:
                    inner = zone[gt + 1 : clo]
                    if inner.casefold() == lf:
                        buf.append(f'<strong><a href="{href}">{inner}</a></strong>')
                        pos += clo + len(blob_hi)
                        linked_stems.add(stem)
                        matched = True
                        break

            if zone.startswith("**"):
                inner_end = zone.find("**", 2)
                if inner_end != -1:
                    inner = zone[2:inner_end]
                    if inner.casefold() == lf:
                        buf.append(f"[**{inner}**]({href})")
                        pos += inner_end + 2
                        linked_stems.add(stem)
                        matched = True
                        break

            ln = len(label)
            if len(zone) >= ln and zone[:ln].casefold() == lf:
                before = segment[pos - 1] if pos > 0 else "\n"
                if _is_wordish(before):
                    continue
                after_idx = pos + ln
                after_ch = segment[after_idx] if after_idx < len(segment) else "\n"

                original = zone[:ln]

                if after_ch == "'" and segment[after_idx + 1 : after_idx + 2] == "s":
                    next_after = segment[after_idx + 2] if after_idx + 2 < len(segment) else "\n"
                    if _is_wordish(next_after):
                        continue
                    buf.append(f"[**{original}**]({href})'s")
                    pos = after_idx + 2
                    linked_stems.add(stem)
                    matched = True
                    break

                if not _is_wordish(after_ch):
                    buf.append(f"[**{original}**]({href})")
                    pos = after_idx
                    linked_stems.add(stem)
                    matched = True
                    break

        if matched:
            continue

        buf.append(segment[pos])
        pos += 1

    return "".join(buf)


def link_zone_middle(middle: str, jobs_sorted: list[tuple[str, str, str]]) -> str:
    linked_stems: set[str] = set()
    _seed_existing_wiki_links(middle, linked_stems)
    parts = _IMG_TAG_INLINE_RE.split(middle)
    out: list[str] = []
    for chunk in parts:
        if chunk and chunk.lower().startswith("<img"):
            out.append(chunk)
        else:
            out.append(_link_text_segment(chunk, jobs_sorted, linked_stems))
    return "".join(out)


def process_file(path: pathlib.Path) -> str:
    raw = path.read_text(encoding="utf-8")
    session_dir = path.parent
    public_dir = session_dir.parent
    if public_dir.name != "public":
        sys.exit(f"Expected session under .../public/sessions; got {path}")

    jobs = collect_entity_jobs(public_dir)
    head, middle, tail = _split_middle_for_linking(raw)
    new_middle = link_zone_middle(middle, jobs)
    return head + new_middle + tail


def _diff_report(orig: str, out: str) -> None:
    print("--- dry-run (use --write to apply) ---")
    for i, (a, b) in enumerate(zip(orig.splitlines(), out.splitlines())):
        if a != b:
            print(f"line {i+1}:\n- {a}\n+ {b}")
    if orig.splitlines() != out.splitlines():
        ol, nl = len(orig.splitlines()), len(out.splitlines())
        if ol != nl:
            print(f"(line count {ol} -> {nl})")


def main() -> None:
    ap = argparse.ArgumentParser(description="Add first-occurrence wiki links to session recaps")
    ap.add_argument(
        "session_md",
        type=pathlib.Path,
        help="Path to public/sessions/DATE.md or the sessions/ directory",
    )
    ap.add_argument("--write", action="store_true", help="Write files in place (default: dry-run)")
    args = ap.parse_args()

    base = args.session_md.resolve()
    paths: list[pathlib.Path]
    if base.is_dir():
        paths = sorted(base.glob("*.md"))
        if not paths:
            sys.exit(f"No *.md in {base}")
    else:
        paths = [base]

    for path in paths:
        if not path.exists():
            sys.exit(f"Not found: {path}")
        out = process_file(path)
        orig = path.read_text(encoding="utf-8")
        if out == orig:
            print(f"{path.name}: no changes.")
            continue
        if args.write:
            path.write_text(out, encoding="utf-8")
            print(f"Wrote: {path}")
        else:
            print(f"{path}:")
            _diff_report(orig, out)


if __name__ == "__main__":
    main()

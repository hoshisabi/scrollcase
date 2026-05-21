#!/usr/bin/env python3
"""
process_session.py -- TTRPG session prep pipeline

Does the mechanical work so Claude Code can do the creative work.

Usage:
    uv run python process_session.py <transcript_file>
    uv run python process_session.py --generate-images <session_date> [--badge] [--force]

Supported transcript formats (auto-detected):
  - NoteCat markdown  (PandoDnD / online campaigns)
  - Raw Speaker: text (SessionKeeper / in-person campaigns)

Stages (normal run):
  1. Parse transcript         → date, speakers, intro segment
  2. Warhorn lookup           → session name, scenario  [NoteCat campaigns only]
  3. Adventure catalog        → code, title, metadata   [NoteCat campaigns only]
  4. Roster questions         → interactive, updates player registry
  5. Write outputs            → DM roster file, context summary, and DM prep prompt

Stage (image run):
  6. Generate achievement images from prompts in the session page
"""

import argparse
import json
import os
import pathlib
import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

from campaign_config import (
    default_portrait_url,
    ensure_campaign_default_portrait_file,
)
import yaml
from dotenv import load_dotenv

SCRIPT_DIR = pathlib.Path(__file__).parent
load_dotenv(SCRIPT_DIR / ".env")

WARHORN_API_ENDPOINT = "https://warhorn.net/graphql"
WARHORN_EVENT_SLUG = "pandodnd"


# -- Helpers -------------------------------------------------------------------

def ask(prompt: str, default: str = None) -> str:
    hint = f" [{default}]" if default else ""
    print(f"\n? {prompt}{hint}: ", end="", flush=True)
    answer = input().strip()
    return answer if answer else (default or "")


def _noprompt_fail(noprompt: bool, question: str) -> None:
    if noprompt:
        print(
            f'ERROR: Interactive prompt required but --noprompt is set: "{question}"',
            file=sys.stderr,
        )
        sys.exit(1)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def format_date(d) -> str:
    return f"{d.strftime('%B')} {d.day}, {d.year}"


# -- Stage 1: Parse transcript -------------------------------------------------

def detect_format(path: pathlib.Path) -> str:
    """Return 'notecat' or 'raw' based on file content."""
    text = path.read_text(encoding="utf-8", errors="ignore")[:1000]
    if re.search(r"\*\*Date\*\*:", text) or re.search(r"\*\*.+?\*\* - \d+:\d+", text):
        return "notecat"
    return "raw"


def parse_raw_transcript(path: pathlib.Path) -> dict:
    """Parse a plain 'Speaker: text' transcript (SessionKeeper / named whisper output)."""
    text = path.read_text(encoding="utf-8")

    # Date from filename: session_transcript_MMDDYY.txt or YYYY-MM-DD anywhere in stem
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.stem)
    if m:
        session_date = datetime.strptime(m.group(1), "%Y-%m-%d").date()
    else:
        m = re.search(r"(\d{6})", path.stem)
        if m:
            session_date = datetime.strptime(m.group(1), "%m%d%y").date()
        else:
            raise ValueError(f"Cannot extract date from filename: {path.name}")

    speakers = list(dict.fromkeys(
        s.strip() for s in re.findall(r"^([^:\n]+):", text, re.MULTILINE)
        if s.strip()
    ))

    intro = "\n".join(text.splitlines()[:120])

    return {
        "date": session_date,
        "date_str": session_date.strftime("%Y-%m-%d"),
        "duration": "unknown",
        "speakers": speakers,
        "transcript": text,
        "intro": intro,
        "source_path": str(path.resolve()),
    }


def parse_notecat(path: pathlib.Path) -> dict:
    text = path.read_text(encoding="utf-8")

    date_match = re.search(r"\*\*Date\*\*:\s*(\w+ \d+, \d{4})", text)
    if not date_match:
        raise ValueError("Could not find date in NoteCat header")
    session_date = datetime.strptime(date_match.group(1), "%B %d, %Y").date()

    duration_match = re.search(r"\*\*Duration\*\*:\s*(.+)", text)
    duration = duration_match.group(1).strip() if duration_match else "unknown"

    speakers = list(dict.fromkeys(
        re.findall(r"^\*\*(.+?)\*\* - \d+:\d+", text, re.MULTILINE)
    ))

    # Filter out system/bot entries (italicised presence lines, not bold speaker lines)
    speakers = [s for s in speakers if s and not s.startswith("*")]

    transcript_start = text.find("## Transcript")
    if transcript_start == -1:
        raise ValueError("Could not find ## Transcript section")
    transcript = text[transcript_start:]

    intro = _extract_intro(transcript, minutes=20)

    return {
        "date": session_date,
        "date_str": session_date.strftime("%Y-%m-%d"),
        "duration": duration,
        "speakers": speakers,
        "transcript": transcript,
        "intro": intro,
        "source_path": str(path.resolve()),
    }


def _extract_intro(transcript: str, minutes: int = 20) -> str:
    time_re = re.compile(r"(\d+):(\d+) (AM|PM)")
    first_minutes = None
    kept = []

    for line in transcript.splitlines():
        m = time_re.search(line)
        if m:
            h, mn, ampm = int(m.group(1)), int(m.group(2)), m.group(3)
            if ampm == "PM" and h != 12:
                h += 12
            elif ampm == "AM" and h == 12:
                h = 0
            total = h * 60 + mn
            if first_minutes is None:
                first_minutes = total
            if total - first_minutes > minutes:
                break
        kept.append(line)

    return "\n".join(kept)


# -- Stage 2: Warhorn lookup ---------------------------------------------------

_WARHORN_QUERY = """
query EventSessions($events: [String!]!, $startsAfter: ISO8601DateTime) {
  eventSessions(events: $events, startsAfter: $startsAfter) {
    nodes {
      name
      startsAt
      uuid
      gmSignups    { user { name } }
      playerSignups { user { name } }
      scenario     { name }
    }
  }
}
"""


def query_warhorn(session_date, token: str, slug_override: str = None) -> Optional[dict]:
    starts_after = datetime(
        session_date.year, session_date.month, session_date.day, tzinfo=timezone.utc
    ) - timedelta(days=1)
    slug = slug_override or WARHORN_EVENT_SLUG

    try:
        resp = requests.post(
            WARHORN_API_ENDPOINT,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "query": _WARHORN_QUERY,
                "variables": {
                    "events": [slug],
                    "startsAfter": starts_after.isoformat(),
                },
            },
            timeout=10,
        )
        resp.raise_for_status()
        nodes = resp.json().get("data", {}).get("eventSessions", {}).get("nodes", [])
        for node in nodes:
            node_date = datetime.fromisoformat(
                node["startsAt"].replace("Z", "+00:00")
            ).date()
            if node_date == session_date:
                return node
        return None
    except Exception as e:
        print(f"  Warhorn query failed: {e}")
        return None


# -- Stage 3: Adventure catalog lookup ----------------------------------------

def lookup_catalog(catalog_dir: pathlib.Path, scenario_name: str) -> Optional[dict]:
    if not catalog_dir or not catalog_dir.exists():
        return None

    needle = scenario_name.upper()
    for f in sorted(catalog_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if not data.get("is_adventure"):
                continue
            for field in ("code", "title", "full_title"):
                val = data.get(field, "")
                if val and (val.upper() in needle or needle in val.upper()):
                    return data
        except (json.JSONDecodeError, KeyError):
            continue
    return None


# -- Stage 4: Player registry & roster ----------------------------------------

def load_registry(path: pathlib.Path) -> list:
    if path.exists():
        return yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return []


def save_registry(path: pathlib.Path, registry: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(registry, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def resolve_slug(
    registry: list,
    player_name: str,
    discord_name: str,
    *,
    slug_override: str | None = None,
    derive_if_missing: bool = False,
    noprompt: bool = False,
) -> str:
    name_lower = player_name.lower()
    for entry in registry:
        if entry["display_name"].lower() == name_lower:
            aliases = entry.setdefault("discord_aliases", [])
            if discord_name and discord_name not in aliases:
                aliases.append(discord_name)
            return entry["slug"]

    default_slug = slugify(player_name.split()[0])
    if slug_override is not None:
        confirmed_slug = slug_override
    elif derive_if_missing:
        confirmed_slug = default_slug
    else:
        print(f"\n  New player: '{player_name}' (Discord: {discord_name})")
        _noprompt_fail(noprompt, "  Page slug (e.g. 'ken')")
        confirmed_slug = ask("  Page slug (e.g. 'ken')", default=default_slug)

    registry.append({
        "slug": confirmed_slug,
        "display_name": player_name,
        "discord_aliases": [discord_name] if discord_name else [],
    })
    return confirmed_slug


def _load_roster_file(path: pathlib.Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        sys.exit(f"Roster file must be a YAML list: {path}")
    return data


def _roster_entry_from_file(entry: dict, registry: list, *, noprompt: bool) -> dict:
    discord_name = entry["discord_name"]
    player_name = entry["player_name"]
    is_dm = bool(entry.get("is_dm"))

    if is_dm:
        return {
            "discord_name": discord_name,
            "player_name": player_name,
            "character_name": None,
            "character_class": None,
            "is_dm": True,
            "slug": None,
        }

    character_name = entry.get("character_name") or None
    character_class = entry.get("character_class") or None
    slug = entry.get("slug")
    if slug is not None:
        resolved_slug = resolve_slug(
            registry,
            player_name,
            discord_name,
            slug_override=str(slug).strip(),
            noprompt=noprompt,
        )
    else:
        resolved_slug = resolve_slug(
            registry,
            player_name,
            discord_name,
            derive_if_missing=True,
            noprompt=noprompt,
        )

    return {
        "discord_name": discord_name,
        "player_name": player_name,
        "character_name": character_name,
        "character_class": character_class,
        "is_dm": False,
        "slug": resolved_slug,
    }


def build_roster_from_file(
    speakers: list,
    registry: list,
    roster_path: pathlib.Path,
    *,
    noprompt: bool = False,
) -> list:
    """Build roster from YAML; prompt interactively for speakers not in the file."""
    entries = _load_roster_file(roster_path)
    by_discord = {e["discord_name"]: e for e in entries if e.get("discord_name")}

    print("\n  Speakers found in transcript:")
    for i, name in enumerate(speakers, 1):
        print(f"    {i}. {name}")

    roster: list[dict] = []
    unmatched: list[str] = []
    dm_set = False

    for discord_name in speakers:
        file_entry = by_discord.get(discord_name)
        if file_entry is None:
            unmatched.append(discord_name)
            continue
        print(f"\n  -- {discord_name} -- [roster file]")
        row = _roster_entry_from_file(file_entry, registry, noprompt=noprompt)
        roster.append(row)
        if row.get("is_dm"):
            dm_set = True

    if unmatched:
        print(f"\n  {len(unmatched)} speaker(s) not in roster file — interactive prompts follow.")
        roster.extend(
            build_roster_interactively(
                unmatched,
                registry,
                noprompt=noprompt,
                dm_set=dm_set,
            )
        )

    return roster


def build_roster_interactively(
    speakers: list,
    registry: list,
    *,
    noprompt: bool = False,
    dm_set: bool = False,
) -> list:
    """Ask the DM to identify each speaker and their character."""
    print("\n  Speakers found in transcript:")
    for i, name in enumerate(speakers, 1):
        print(f"    {i}. {name}")

    roster = []

    for discord_name in speakers:
        print(f"\n  -- {discord_name} --")

        is_dm = False
        if not dm_set:
            _noprompt_fail(noprompt, "  Is this the DM?")
            flag = ask("  Is this the DM?", default="n").lower()
            if flag in ("y", "yes"):
                is_dm = True
                dm_set = True

        if is_dm:
            _noprompt_fail(noprompt, "  DM's name")
            player_name = ask("  DM's name", default=discord_name.split()[0])
            roster.append({
                "discord_name": discord_name,
                "player_name": player_name,
                "character_name": None,
                "character_class": None,
                "is_dm": True,
                "slug": None,
            })
            continue

        # Try to parse player/character from Discord name
        player_name, character_name = _parse_discord_name(discord_name)

        _noprompt_fail(noprompt, "  Player name")
        player_name = ask("  Player name", default=player_name)
        _noprompt_fail(noprompt, "  Character name")
        character_name = ask("  Character name", default=character_name or "") or None
        _noprompt_fail(noprompt, "  Class (optional)")
        character_class = ask("  Class (optional)") or None

        slug = resolve_slug(registry, player_name, discord_name, noprompt=noprompt)

        roster.append({
            "discord_name": discord_name,
            "player_name": player_name,
            "character_name": character_name,
            "character_class": character_class,
            "is_dm": False,
            "slug": slug,
        })

    return roster


def _parse_discord_name(name: str) -> tuple[str, Optional[str]]:
    """Heuristic: 'handle(Player-Character)' or 'Handle (Character)' → (player, character)."""
    # Pattern: something(Player-Character)
    m = re.match(r"[^(]+\((.+?)\)", name)
    if m:
        inner = m.group(1)
        parts = re.split(r"[-–]", inner, maxsplit=1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
        return inner.strip(), None

    # Pattern: Word Word (Character)  -- e.g. "Ken B. (Kenistopheles)"
    m = re.match(r"(.+?)\s*\((.+?)\)$", name)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Plain name or opaque handle -- use as-is for player, no character
    parts = name.split()
    player = parts[-1] if len(parts) > 1 else name
    return player, None


# -- Stage 5: Write outputs ----------------------------------------------------

def write_roster_file(out_path: pathlib.Path, date_str: str, adventure: dict, roster: list):
    lines = [
        f"# Session Roster -- {date_str}",
        "",
        f"**Adventure**: {adventure.get('full_title', 'Unknown')}",
        "",
        "| Discord Handle | Player | Character | Class |",
        "|---|---|---|---|",
    ]
    for r in roster:
        lines.append(
            f"| {r['discord_name']} "
            f"| {r['player_name']} "
            f"| {r.get('character_name') or '--'} "
            f"| {r.get('character_class') or '--'} |"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Written: {out_path}")


def write_dm_prep_prompt(
    out_path: pathlib.Path,
    notecat: dict,
    roster: list,
    campaign_dir: pathlib.Path,
    campaign: dict,
):
    """Write a pre-filled DM assistant prompt ready to paste into a fresh Claude conversation."""
    script_dir = pathlib.Path(__file__).parent
    template_path = script_dir / "prompt_dm_assistant.md"

    # Extract the prompt body from between the ``` markers in the template
    sections_text = ""
    if template_path.exists():
        raw = template_path.read_text(encoding="utf-8")
        parts = raw.split("```")
        body = parts[1].strip() if len(parts) >= 3 else raw.strip()
        marker = "Write a DM assistant report"
        if marker in body:
            sections_text = body[body.index(marker):]

    dm_name = campaign.get("dm", "Unknown")
    campaign_name = campaign.get("name", campaign_dir.name)

    players = [r for r in roster if not r.get("is_dm")]
    players_inline = ", ".join(
        f"{r['player_name']} playing {r.get('character_name') or '(unnamed)'}"
        for r in players
    )

    # Collect wiki file paths that exist on disk
    wiki_paths = []
    for stem in ["threads.md", "timeline.md"]:
        p = campaign_dir / "dm" / stem
        if p.exists():
            wiki_paths.append(str(p))
    pcs_dir = campaign_dir / "dm" / "characters" / "pcs"
    if pcs_dir.exists():
        wiki_paths.extend(sorted(str(p) for p in pcs_dir.glob("*.md")))
    npcs_dir = campaign_dir / "dm" / "characters" / "npcs"
    if npcs_dir.exists():
        wiki_paths.extend(sorted(str(p) for p in npcs_dir.glob("*.md")))
    wiki_block = "\n".join(f"  {p}" for p in wiki_paths) or "  (no wiki files found)"

    save_path = out_path.parent / f"{notecat['date_str']}-prep.md"

    lines = [
        f"# DM Prep Prompt — {format_date(notecat['date'])}",
        "",
        "Paste this into a fresh Claude conversation (separate from the player recap).",
        "Save Claude's output to:",
        f"  `{save_path}`",
        "",
        "---",
        "",
        f"You are a D&D session analyst writing a DM assistant report for {dm_name}, the Dungeon Master.",
        "",
        f"Campaign: {campaign_name}",
        f"Session date: {format_date(notecat['date'])}",
        f"Players: {dm_name} (DM)" + (f", {players_inline}" if players_inline else ""),
        "",
        "<wiki>",
        "Paste the contents of these files, or in Claude Code ask it to read them:",
        "",
        wiki_block,
        "</wiki>",
        "",
        "<transcript>",
        "Paste the corrected transcript, or in Claude Code share this path:",
        f"  {notecat['source_path']}",
        "</transcript>",
        "",
        sections_text,
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(l for l in lines if l is not None), encoding="utf-8")
    print(f"  Written: {out_path}")


def write_context_summary(
    out_path: pathlib.Path,
    notecat: dict,
    adventure: dict,
    roster: list,
    warhorn_session: Optional[dict],
    *,
    campaign_dir: pathlib.Path,
    campaign: dict,
):
    """Write a context file for use in a Claude Code conversation."""
    dm = next((r for r in roster if r.get("is_dm")), None)
    players = [r for r in roster if not r.get("is_dm")]

    players_md = "\n".join(
        f"- **{r['player_name']}** as **{r.get('character_name') or '(unnamed)'}**"
        + (f" -- {r['character_class']}" if r.get("character_class") else "")
        for r in players
    )

    warhorn_players = ""
    if warhorn_session and warhorn_session.get("playerSignups"):
        names = [s["user"]["name"] for s in warhorn_session["playerSignups"]]
        warhorn_players = f"\n**Warhorn signups**: {', '.join(names)}"

    lines = [
        f"# Session Context -- {notecat['date_str']}",
        "",
        "## Adventure",
        f"**Code**: {adventure.get('code', 'Unknown')}",
        f"**Title**: {adventure.get('full_title', 'Unknown')}",
        f"**Level range**: {adventure.get('level_range', '?')}  "
        f"**APL**: {adventure.get('apl', '?')}  "
        f"**Duration**: {adventure.get('hours', '?')}h",
        "",
        "## Session",
        f"**Date**: {format_date(notecat['date'])}",
        f"**Duration**: {notecat['duration']}",
        f"**DM**: {dm['player_name'] if dm else 'Unknown'}",
        warhorn_players,
        "",
        "## Roster",
        players_md,
        "",
        "## Transcript",
        f"**Source file**: `{notecat['source_path']}`",
        "",
        "---",
        "",
        "## Next step",
        "",
        "In Claude Code, share this file and the transcript path, then ask Claude to:",
        "1. Read the intro segment and confirm/correct the roster",
        "2. Generate the session recap, player highlights, and achievements.",
        "   For **Player Highlights**, use `<div class=\"highlight\">`, `<img class=\"highlight-portrait\" src=\"...\">`, "
        "and `<p><strong>...</strong> — …</p>` — same flex row layout as achievements (see scrollcase **style_guide.md**, *Player Highlights*). "
        "**src** for each highlight: the character/NPC **`image`** from `public/characters/*.md` or `public/npcs/*.md` when set; "
        f"otherwise the campaign generic portrait (`{default_portrait_url(campaign_dir, campaign)}` — "
        "`campaign.yaml` `default_portrait`, or `public/images/default-portrait.png`).",
        "3. Write the public session page to:",
        f"   `{out_path.parent.parent.parent / 'public' / 'sessions' / (notecat['date_str'] + '.md')}`",
        "4. Once achievement image prompts are confirmed, run either:",
        f"   `uv run python process_session.py --generate-images {notecat['date_str']} --campaign-dir <same path as this script>`",
        "   or:",
        f"   `uv run python generate_artwork.py public/sessions/{notecat['date_str']}.md`",
        "   Both write the same filenames under `public/sessions/images/`. Add `--badge` on `process_session.py`, or pass `--badge` to `generate_artwork.py`, for shield cropping.",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(l for l in lines if l is not None), encoding="utf-8")
    print(f"  Written: {out_path}")


# -- Stage 6: Generate achievement images -------------------------------------

def generate_images_for_session(
    session_date_str: str,
    campaign_dir: pathlib.Path,
    *,
    badge: bool = False,
    force: bool = False,
) -> None:
    """Same pipeline as ``generate_artwork.py`` — YAML ``image_prompt`` or session HTML comments."""
    from generate_artwork import generate_session_images

    try:
        total = generate_session_images(
            campaign_dir=campaign_dir,
            session_date_str=session_date_str,
            badge=badge,
            force=force,
        )
    except FileNotFoundError as e:
        sys.exit(str(e))
    except ValueError as e:
        sys.exit(str(e))
    print(f"\nDone. {total} image(s) generated.")


# -- Main ----------------------------------------------------------------------

def load_campaign(campaign_dir: pathlib.Path) -> dict:
    config_path = campaign_dir / "campaign.yaml"
    if not config_path.exists():
        return {}
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def main():
    parser = argparse.ArgumentParser(
        description="scrollcase session pipeline"
    )
    parser.add_argument("notecat_file", nargs="?", help="Transcript file (NoteCat markdown or raw Speaker: text)")
    parser.add_argument(
        "--generate-images",
        metavar="DATE",
        help="Generate achievement images for a session (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--badge",
        action="store_true",
        help="With --generate-images: shield-crop badges (matches generate_artwork.py --badge)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="With --generate-images: overwrite existing PNGs",
    )
    parser.add_argument(
        "--campaign-dir",
        default=os.getenv("CAMPAIGN_DIR"),
        help="Campaign root directory (must contain campaign.yaml). "
             "Can also be set via CAMPAIGN_DIR in .env.",
    )
    parser.add_argument(
        "--noprompt",
        action="store_true",
        help="Fail instead of prompting interactively (use with --roster-file / --scenario-name)",
    )
    parser.add_argument(
        "--roster-file",
        type=pathlib.Path,
        metavar="PATH",
        help="YAML roster entries keyed by discord_name (see style_guide / README)",
    )
    parser.add_argument(
        "--scenario-name",
        metavar="TEXT",
        help="Adventure/scenario name when Warhorn lookup fails or is skipped",
    )
    args = parser.parse_args()

    if args.badge and not args.generate_images:
        parser.error("--badge requires --generate-images DATE")
    if args.force and not args.generate_images:
        parser.error("--force requires --generate-images DATE")

    if not args.campaign_dir:
        parser.error(
            "--campaign-dir is required (or set CAMPAIGN_DIR in .env)"
        )

    campaign_dir = pathlib.Path(args.campaign_dir).expanduser()

    campaign = load_campaign(campaign_dir)
    if campaign:
        print(f"\nCampaign: {campaign.get('name', campaign_dir.name)} (DM: {campaign.get('dm', '?')})")
    copied = ensure_campaign_default_portrait_file(campaign_dir, campaign)
    if copied:
        print(f"  Generic portrait: copied scrollcase default → {copied.relative_to(campaign_dir)}")

    # Resolve catalog dir: campaign.yaml > env var
    catalog_dir_raw = campaign.get("catalog_dir") or os.getenv("AL_CATALOG_DIR")
    catalog_dir = pathlib.Path(catalog_dir_raw).expanduser() if catalog_dir_raw else None

    # Resolve warhorn slug from campaign.yaml
    warhorn_slug_override = campaign.get("warhorn_slug")

    # Image generation mode
    if args.generate_images:
        generate_images_for_session(
            args.generate_images,
            campaign_dir,
            badge=args.badge,
            force=args.force,
        )
        return

    if not args.notecat_file:
        parser.error("notecat_file is required unless --generate-images is used")

    if args.roster_file and not args.roster_file.exists():
        parser.error(f"Roster file not found: {args.roster_file}")

    notecat_path = pathlib.Path(args.notecat_file).expanduser()
    if not notecat_path.exists():
        sys.exit(f"Not found: {notecat_path}")

    warhorn_token = os.getenv("WARHORN_APPLICATION_TOKEN", "")

    registry_path = campaign_dir / "dm" / "player-registry.yaml"
    registry = load_registry(registry_path)

    # -- 1. Parse --
    fmt = detect_format(notecat_path)
    print(f"\n-- 1. Parsing transcript ({fmt}) ----------------------------")
    if fmt == "notecat":
        notecat = parse_notecat(notecat_path)
    else:
        notecat = parse_raw_transcript(notecat_path)
    print(f"  Date:     {notecat['date_str']}")
    print(f"  Duration: {notecat['duration']}")
    print(f"  Speakers: {len(notecat['speakers'])} found - {', '.join(notecat['speakers'])}")

    # -- 2. Warhorn --
    warhorn_session = None
    if warhorn_slug_override:
        print("\n-- 2. Warhorn lookup ----------------------------------------")
        if warhorn_token:
            warhorn_session = query_warhorn(notecat["date"], warhorn_token, slug_override=warhorn_slug_override)
        if warhorn_session:
            scenario_name = warhorn_session.get("scenario", {}).get("name", "")
            print(f"  Session:  {warhorn_session.get('name')}")
            print(f"  Scenario: {scenario_name}")
        else:
            print("  No Warhorn session found for this date")
            if args.scenario_name:
                scenario_name = args.scenario_name
            else:
                _noprompt_fail(args.noprompt, "  Adventure code or name")
                scenario_name = ask("  Adventure code or name")
    else:
        print("\n-- 2. Warhorn lookup ----------------------- [skipped, no warhorn_slug]")
        scenario_name = args.scenario_name or ""

    # -- 3. Catalog --
    if warhorn_slug_override or scenario_name:
        print("\n-- 3. Adventure catalog -------------------------------------")
        adventure = lookup_catalog(catalog_dir, scenario_name) if scenario_name else None
        if adventure:
            print(f"  Found: {adventure['full_title']}")
        else:
            print("  Not found in catalog")
            _noprompt_fail(args.noprompt, "  Adventure code (e.g. PS-DC-PUB-08)")
            code = ask("  Adventure code (e.g. PS-DC-PUB-08)")
            _noprompt_fail(args.noprompt, "  Adventure title")
            title = ask("  Adventure title")
            adventure = {"code": code, "title": title, "full_title": f"{code} {title}"}
    else:
        print("\n-- 3. Adventure catalog ------------------- [skipped, no warhorn_slug]")
        adventure = {"code": "", "title": campaign.get("name", ""), "full_title": campaign.get("name", "")}
    adventure["date"] = notecat["date_str"]

    # -- 4. Roster --
    print("\n-- 4. Roster -------------------------------------------")
    if args.roster_file:
        roster = build_roster_from_file(
            notecat["speakers"],
            registry,
            args.roster_file.expanduser(),
            noprompt=args.noprompt,
        )
    else:
        roster = build_roster_interactively(
            notecat["speakers"],
            registry,
            noprompt=args.noprompt,
        )
    save_registry(registry_path, registry)

    # -- 5. Write outputs --
    print("\n-- 5. Writing outputs ----------------------------------")

    write_roster_file(
        out_path=campaign_dir / "dm" / "sessions" / f"{notecat['date_str']}-roster.md",
        date_str=notecat["date_str"],
        adventure=adventure,
        roster=roster,
    )

    write_context_summary(
        out_path=campaign_dir / "dm" / "sessions" / f"{notecat['date_str']}-context.md",
        notecat=notecat,
        adventure=adventure,
        roster=roster,
        warhorn_session=warhorn_session,
        campaign_dir=campaign_dir,
        campaign=campaign,
    )

    write_dm_prep_prompt(
        out_path=campaign_dir / "dm" / "sessions" / f"{notecat['date_str']}-dm-prompt.md",
        notecat=notecat,
        roster=roster,
        campaign_dir=campaign_dir,
        campaign=campaign,
    )

    context_path = campaign_dir / "dm" / "sessions" / (notecat["date_str"] + "-context.md")
    dm_prompt_path = campaign_dir / "dm" / "sessions" / (notecat["date_str"] + "-dm-prompt.md")
    print(f"\n✓ Prep complete.")
    print(f"\n  Player recap → open in Claude Code:")
    print(f"    {context_path}")
    print(f"\n  DM prep → paste into a fresh Claude conversation:")
    print(f"    {dm_prompt_path}")


if __name__ == "__main__":
    main()

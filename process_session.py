#!/usr/bin/env python3
"""
process_session.py — Pandemonium Pub Crawl session prep pipeline

Does the mechanical work so Claude Code can do the creative work.

Usage:
    uv run python process_session.py <notecat_markdown_file>
    uv run python process_session.py --generate-images <session_date>  (e.g. 2026-05-13)

Stages (normal run):
  1. Parse NoteCat markdown  → date, speakers, intro segment
  2. Warhorn lookup           → session name, scenario
  3. Adventure catalog        → code, title, metadata
  4. Roster questions         → interactive, updates player registry
  5. Write outputs            → DM roster file + context summary for Claude Code

Stage (image run):
  6. Generate achievement images from prompts in the session page
"""

import argparse
import json
import os
import pathlib
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests
import yaml
from dotenv import load_dotenv

SCRIPT_DIR = pathlib.Path(__file__).parent
load_dotenv(SCRIPT_DIR / ".env")

WARHORN_API_ENDPOINT = "https://warhorn.net/graphql"
WARHORN_EVENT_SLUG = "pandodnd"


# ── Helpers ───────────────────────────────────────────────────────────────────

def ask(prompt: str, default: str = None) -> str:
    hint = f" [{default}]" if default else ""
    print(f"\n❓ {prompt}{hint}: ", end="", flush=True)
    answer = input().strip()
    return answer if answer else (default or "")


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def format_date(d) -> str:
    return f"{d.strftime('%B')} {d.day}, {d.year}"


# ── Stage 1: Parse NoteCat ────────────────────────────────────────────────────

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


# ── Stage 2: Warhorn lookup ───────────────────────────────────────────────────

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


# ── Stage 3: Adventure catalog lookup ────────────────────────────────────────

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


# ── Stage 4: Player registry & roster ────────────────────────────────────────

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


def resolve_slug(registry: list, player_name: str, discord_name: str) -> str:
    name_lower = player_name.lower()
    for entry in registry:
        if entry["display_name"].lower() == name_lower:
            aliases = entry.setdefault("discord_aliases", [])
            if discord_name and discord_name not in aliases:
                aliases.append(discord_name)
            return entry["slug"]

    default_slug = slugify(player_name.split()[0])
    print(f"\n  New player: '{player_name}' (Discord: {discord_name})")
    confirmed_slug = ask("  Page slug (e.g. 'ken')", default=default_slug)

    registry.append({
        "slug": confirmed_slug,
        "display_name": player_name,
        "discord_aliases": [discord_name] if discord_name else [],
    })
    return confirmed_slug


def build_roster_interactively(speakers: list, registry: list) -> list:
    """Ask the DM to identify each speaker and their character."""
    print("\n  Speakers found in transcript:")
    for i, name in enumerate(speakers, 1):
        print(f"    {i}. {name}")

    roster = []
    dm_set = False

    for discord_name in speakers:
        print(f"\n  ── {discord_name} ──")

        is_dm = False
        if not dm_set:
            flag = ask("  Is this the DM?", default="n").lower()
            if flag in ("y", "yes"):
                is_dm = True
                dm_set = True

        if is_dm:
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

        player_name = ask("  Player name", default=player_name)
        character_name = ask("  Character name", default=character_name or "") or None
        character_class = ask("  Class (optional)") or None

        slug = resolve_slug(registry, player_name, discord_name)

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

    # Pattern: Word Word (Character)  — e.g. "Ken B. (Kenistopheles)"
    m = re.match(r"(.+?)\s*\((.+?)\)$", name)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Plain name or opaque handle — use as-is for player, no character
    parts = name.split()
    player = parts[-1] if len(parts) > 1 else name
    return player, None


# ── Stage 5: Write outputs ────────────────────────────────────────────────────

def write_roster_file(out_path: pathlib.Path, date_str: str, adventure: dict, roster: list):
    lines = [
        f"# Session Roster — {date_str}",
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
            f"| {r.get('character_name') or '—'} "
            f"| {r.get('character_class') or '—'} |"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Written: {out_path}")


def write_context_summary(
    out_path: pathlib.Path,
    notecat: dict,
    adventure: dict,
    roster: list,
    warhorn_session: Optional[dict],
):
    """Write a context file for use in a Claude Code conversation."""
    dm = next((r for r in roster if r.get("is_dm")), None)
    players = [r for r in roster if not r.get("is_dm")]

    players_md = "\n".join(
        f"- **{r['player_name']}** as **{r.get('character_name') or '(unnamed)'}**"
        + (f" — {r['character_class']}" if r.get("character_class") else "")
        for r in players
    )

    warhorn_players = ""
    if warhorn_session and warhorn_session.get("playerSignups"):
        names = [s["user"]["name"] for s in warhorn_session["playerSignups"]]
        warhorn_players = f"\n**Warhorn signups**: {', '.join(names)}"

    lines = [
        f"# Session Context — {notecat['date_str']}",
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
        "2. Generate the session recap, player highlights, and achievements",
        "3. Write the public session page to:",
        f"   `{out_path.parent.parent.parent / 'public' / 'sessions' / (notecat['date_str'] + '.md')}`",
        "4. Once achievement image prompts are confirmed, run:",
        f"   `uv run python process_session.py --generate-images {notecat['date_str']}`",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(l for l in lines if l is not None), encoding="utf-8")
    print(f"  Written: {out_path}")


# ── Stage 6: Generate achievement images ─────────────────────────────────────

def generate_images_for_session(session_date_str: str, campaign_dir: pathlib.Path):
    """Read achievement image prompts from the session page and generate badges."""
    from google import genai
    from google.genai import types

    session_page = campaign_dir / "public" / "sessions" / f"{session_date_str}.md"
    if not session_page.exists():
        sys.exit(f"Session page not found: {session_page}")

    text = session_page.read_text(encoding="utf-8")

    # Find image prompts: lines like  image_prompt: "..."  in the page
    # Convention: achievements are marked with <!-- image_prompt: ... --> comments
    # or we look for the achievement badge img tags to find which images are missing
    prompts = re.findall(r"<!--\s*image_prompt:\s*(.+?)\s*-->", text)

    if not prompts:
        print("No image prompts found in session page.")
        print("Add prompts as HTML comments above each achievement:")
        print("  <!-- image_prompt: bold vintage woodcut... -->")
        return

    client = genai.Client(api_key=os.getenv("GOOGLE_KEY"))
    images_dir = campaign_dir / "public" / "sessions" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    for i, prompt in enumerate(prompts):
        filename = f"{session_date_str}-achievement-{i+1}.png"
        out_path = images_dir / filename
        if out_path.exists():
            print(f"  [{i+1}/{len(prompts)}] Skipping (already exists): {filename}")
            continue
        if i > 0:
            time.sleep(6)
        print(f"  [{i+1}/{len(prompts)}] Generating: {filename}")
        try:
            resp = client.models.generate_images(
                model="imagen-4.0-fast-generate-001",
                prompt=prompt,
                config=types.GenerateImagesConfig(number_of_images=1),
            )
            resp.generated_images[0].image.save(out_path)
            print(f"    Done: {filename}")
        except Exception as e:
            print(f"    Failed: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def load_campaign(campaign_dir: pathlib.Path) -> dict:
    config_path = campaign_dir / "campaign.yaml"
    if not config_path.exists():
        return {}
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def main():
    parser = argparse.ArgumentParser(
        description="scrollcase session pipeline"
    )
    parser.add_argument("notecat_file", nargs="?", help="NoteCat markdown file")
    parser.add_argument(
        "--generate-images",
        metavar="DATE",
        help="Generate achievement images for a session (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--campaign-dir",
        default=os.getenv("PANDODND_CAMPAIGN_DIR"),
        help="Campaign root directory (must contain campaign.yaml)",
    )
    args = parser.parse_args()

    campaign_dir = pathlib.Path(
        args.campaign_dir or ask("Campaign directory")
    ).expanduser()

    campaign = load_campaign(campaign_dir)
    if campaign:
        print(f"\nCampaign: {campaign.get('name', campaign_dir.name)} (DM: {campaign.get('dm', '?')})")

    # Resolve catalog dir: campaign.yaml > env var
    catalog_dir_raw = campaign.get("catalog_dir") or os.getenv("AL_CATALOG_DIR")
    catalog_dir = pathlib.Path(catalog_dir_raw).expanduser() if catalog_dir_raw else None

    # Resolve warhorn slug from campaign.yaml
    warhorn_slug_override = campaign.get("warhorn_slug")

    # Image generation mode
    if args.generate_images:
        generate_images_for_session(args.generate_images, campaign_dir)
        return

    if not args.notecat_file:
        parser.error("notecat_file is required unless --generate-images is used")

    notecat_path = pathlib.Path(args.notecat_file).expanduser()
    if not notecat_path.exists():
        sys.exit(f"Not found: {notecat_path}")

    warhorn_token = os.getenv("WARHORN_APPLICATION_TOKEN", "")

    registry_path = campaign_dir / "dm" / "player-registry.yaml"
    registry = load_registry(registry_path)

    # ── 1. Parse ──
    print("\n── 1. Parsing NoteCat ──────────────────────────────────")
    notecat = parse_notecat(notecat_path)
    print(f"  Date:     {notecat['date_str']}")
    print(f"  Duration: {notecat['duration']}")
    print(f"  Speakers: {len(notecat['speakers'])} found")

    # ── 2. Warhorn ──
    print("\n── 2. Warhorn lookup ───────────────────────────────────")
    warhorn_session = None
    if warhorn_token:
        warhorn_session = query_warhorn(notecat["date"], warhorn_token, slug_override=warhorn_slug_override)

    if warhorn_session:
        scenario_name = warhorn_session.get("scenario", {}).get("name", "")
        print(f"  Session:  {warhorn_session.get('name')}")
        print(f"  Scenario: {scenario_name}")
    else:
        print("  No Warhorn session found for this date")
        scenario_name = ask("  Adventure code or name")

    # ── 3. Catalog ──
    print("\n── 3. Adventure catalog ────────────────────────────────")
    adventure = lookup_catalog(catalog_dir, scenario_name) if scenario_name else None
    if adventure:
        print(f"  Found: {adventure['full_title']}")
    else:
        print("  Not found in catalog")
        code = ask("  Adventure code (e.g. PS-DC-PUB-08)")
        title = ask("  Adventure title")
        adventure = {"code": code, "title": title, "full_title": f"{code} {title}"}
    adventure["date"] = notecat["date_str"]

    # ── 4. Roster ──
    print("\n── 4. Roster ───────────────────────────────────────────")
    roster = build_roster_interactively(notecat["speakers"], registry)
    save_registry(registry_path, registry)

    # ── 5. Write outputs ──
    print("\n── 5. Writing outputs ──────────────────────────────────")

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
    )

    print(f"\n✓ Prep complete. Open the context file in Claude Code to continue:")
    print(f"  {campaign_dir / 'dm' / 'sessions' / (notecat['date_str'] + '-context.md')}")


if __name__ == "__main__":
    main()

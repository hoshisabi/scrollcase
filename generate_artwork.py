#!/usr/bin/env python3
"""Generate campaign artwork from frontmatter image_prompt fields or a direct prompt.

Frontmatter mode (one or more markdown files, or a directory scan):
    uv run python generate_artwork.py public/npcs/clod.md
    uv run python generate_artwork.py --scan npcs
    uv run python generate_artwork.py --scan sessions

One-off mode (prompt provided directly):
    uv run python generate_artwork.py --prompt "..." --name durok --type npc

Prefix layering (applied additively, outermost first):
    --prefix → campaign.yaml image_prompt_prefix → frontmatter image_prompt_prefix → per-image prompt

To replace the composed prompt entirely for all images, use --prompt-override "full text".
To regenerate only one image from a list, use --image N (1-based) with a single FILE argument.
"""
import os
import time
import argparse
import pathlib
import yaml
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).parent / ".env")

from google import genai
from google.genai import types

CAMPAIGN_DIR = (pathlib.Path(__file__).parent / os.environ["CAMPAIGN_DIR"]).resolve()

SCAN_DIRS = {
    "characters": CAMPAIGN_DIR / "public" / "characters",
    "npcs":       CAMPAIGN_DIR / "public" / "npcs",
    "locations":  CAMPAIGN_DIR / "public" / "locations",
    "sessions":   CAMPAIGN_DIR / "public" / "sessions",
}

TYPE_DIRS = {
    "characters": CAMPAIGN_DIR / "public" / "characters" / "images",
    "npcs":       CAMPAIGN_DIR / "public" / "npcs" / "images",
    "locations":  CAMPAIGN_DIR / "public" / "locations" / "images",
    "other":      CAMPAIGN_DIR / "public" / "images",
}


def parse_frontmatter(path: pathlib.Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    try:
        end = text.index("---", 3)
    except ValueError:
        return {}
    return yaml.safe_load(text[3:end]) or {}


def load_campaign_prefix() -> str:
    config = CAMPAIGN_DIR / "campaign.yaml"
    if not config.exists():
        return ""
    data = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    return (data.get("image_prompt_prefix") or "").strip()


def build_prompt(
    per_image: str,
    cli_prefix: str,
    campaign_prefix: str,
    file_prefix: str,
    prompt_override: str,
) -> str:
    if prompt_override:
        return prompt_override.strip()
    parts = [p.strip(" ,") for p in [cli_prefix, campaign_prefix, file_prefix, per_image] if p and p.strip()]
    return ", ".join(parts)


def output_paths(md_path: pathlib.Path, count: int) -> list[pathlib.Path]:
    images_dir = md_path.parent / "images"
    stem = md_path.stem
    if count == 1:
        return [images_dir / f"{stem}.png"]
    return [images_dir / f"{stem}-{i + 1}.png" for i in range(count)]


def generate_one(client, prompt: str, out_path: pathlib.Path, model: str, force: bool = False) -> bool:
    """Generate a single image. Returns True if generated, False if skipped."""
    if out_path.exists() and not force:
        print(f"  skip (exists): {out_path.name}")
        return False

    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"  generating: {out_path.name}")
    print(f"  prompt: {prompt[:120]}{'...' if len(prompt) > 120 else ''}")

    response = client.models.generate_images(
        model=model,
        prompt=prompt,
        config=types.GenerateImagesConfig(number_of_images=1),
    )
    response.generated_images[0].image.save(out_path)
    print(f"  saved: {out_path}")
    return True


def process_file(
    md_path: pathlib.Path,
    client,
    model: str,
    delay: float,
    force: bool = False,
    cli_prefix: str = "",
    campaign_prefix: str = "",
    prompt_override: str = "",
    image_index: int = None,
) -> int:
    """Process one markdown file. Returns number of images generated."""
    fm = parse_frontmatter(md_path)
    raw = fm.get("image_prompt")
    if not raw:
        return 0

    prompts = raw if isinstance(raw, list) else [raw]
    paths = output_paths(md_path, len(prompts))
    file_prefix = (fm.get("image_prompt_prefix") or "").strip()

    if image_index is not None:
        idx = image_index - 1
        if idx < 0 or idx >= len(prompts):
            print(f"  error: --image {image_index} is out of range (file has {len(prompts)} prompt(s))")
            return 0
        prompts = [prompts[idx]]
        paths = [paths[idx]]

    print(f"\n{md_path.relative_to(CAMPAIGN_DIR)}  ({len(prompts)} prompt(s))")

    generated = 0
    for i, (per_image, out_path) in enumerate(zip(prompts, paths)):
        if i > 0:
            time.sleep(delay)
        final_prompt = build_prompt(per_image, cli_prefix, campaign_prefix, file_prefix, prompt_override)
        if generate_one(client, final_prompt, out_path, model, force=force):
            generated += 1

    return generated


def main():
    parser = argparse.ArgumentParser(description="Generate campaign artwork")
    parser.add_argument("files", nargs="*", metavar="FILE",
                        help="Markdown file(s) to process")
    parser.add_argument("--scan", choices=SCAN_DIRS.keys(), metavar="TYPE",
                        help=f"Scan all .md files in a wiki directory ({', '.join(SCAN_DIRS)})")
    parser.add_argument("--prompt", metavar="TEXT",
                        help="One-off mode: full image prompt (no prefix layering applied)")
    parser.add_argument("--name", metavar="NAME",
                        help="One-off mode: output filename without extension (required with --prompt)")
    parser.add_argument("--type", choices=TYPE_DIRS.keys(), default="other", dest="img_type",
                        help="One-off mode: output directory type (default: other)")
    parser.add_argument("--model", default="imagen-4.0-fast-generate-001",
                        help="Imagen model to use")
    parser.add_argument("--delay", type=float, default=6.0,
                        help="Seconds between API requests (default: 6)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing images")
    parser.add_argument("--prefix", metavar="TEXT",
                        help="Prepend TEXT to all prompts (before campaign and file prefixes)")
    parser.add_argument("--prompt-override", metavar="TEXT", dest="prompt_override",
                        help="Use TEXT as the complete prompt for all images, bypassing prefix layering")
    parser.add_argument("--image", type=int, metavar="N", dest="image_index",
                        help="Only generate image N from a list (1-based); requires a single FILE argument")
    args = parser.parse_args()

    if args.prompt and not args.name:
        parser.error("--prompt requires --name")
    if args.image_index is not None and (args.scan or len(args.files) != 1):
        parser.error("--image requires exactly one FILE argument (not --scan or multiple files)")
    if not args.prompt and not args.files and not args.scan:
        parser.error("Provide FILE(s), --scan TYPE, or --prompt TEXT --name NAME")

    campaign_prefix = load_campaign_prefix()
    client = genai.Client(api_key=os.environ["GOOGLE_KEY"])
    total = 0

    if args.prompt:
        out_path = TYPE_DIRS[args.img_type] / f"{args.name}.png"
        print(f"\none-off: {args.name} ({args.img_type})")
        if generate_one(client, args.prompt, out_path, args.model, force=args.force):
            total += 1
    else:
        md_files: list[pathlib.Path] = []
        if args.scan:
            md_files.extend(sorted(SCAN_DIRS[args.scan].glob("*.md")))
        for f in args.files:
            p = pathlib.Path(f)
            if not p.is_absolute():
                p = CAMPAIGN_DIR / p
            md_files.append(p.resolve())

        for md_path in md_files:
            total += process_file(
                md_path,
                client,
                args.model,
                args.delay,
                force=args.force,
                cli_prefix=args.prefix or "",
                campaign_prefix=campaign_prefix,
                prompt_override=args.prompt_override or "",
                image_index=args.image_index,
            )

    print(f"\nDone. {total} image(s) generated.")


if __name__ == "__main__":
    main()

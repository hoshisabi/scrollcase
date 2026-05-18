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

Shield badge post-process (achievement-style crop):
    --badge / --badge-only  (also --badge-size, --badge-width, --badge-color)
"""
import os
import re
import random
import time
import argparse
import pathlib
import yaml
from dotenv import load_dotenv
from PIL import Image, ImageChops, ImageDraw, ImageFilter

load_dotenv(pathlib.Path(__file__).parent / ".env")

from google import genai
from google.genai import types

SCROLLCASE_DIR = pathlib.Path(__file__).parent.resolve()


def campaign_root_from_env() -> pathlib.Path:
    """Campaign wiki root when using CAMPAIGN_DIR in scrollcase/.env (relative to scrollcase/)."""
    return (SCROLLCASE_DIR / os.environ["CAMPAIGN_DIR"]).resolve()


def scan_dirs(root: pathlib.Path) -> dict[str, pathlib.Path]:
    return {
        "characters": root / "public" / "characters",
        "npcs": root / "public" / "npcs",
        "locations": root / "public" / "locations",
        "sessions": root / "public" / "sessions",
    }


def type_dirs(root: pathlib.Path) -> dict[str, pathlib.Path]:
    return {
        "characters": root / "public" / "characters" / "images",
        "npcs": root / "public" / "npcs" / "images",
        "locations": root / "public" / "locations" / "images",
        "other": root / "public" / "images",
    }


BADGE_COLOR_DEFAULT = (210, 160, 50)   # warm amber
BADGE_SIZE_DEFAULT  = 512
BADGE_WIDTH_DEFAULT = 20               # border ring width at output size
BADGE_MARGIN        = 6               # gap between canvas edge and outer shield edge
BADGE_FRINGE        = 4               # pixels of rough outer edge (worn stamp effect)


def _shield_pts(size: int, inset: int) -> list[tuple[int, int]]:
    """Five-point heraldic shield polygon: flat top, vertical sides, V to bottom center."""
    top  = inset
    bot  = size - inset
    left = inset
    right = size - inset
    cx   = size // 2
    taper_y = inset + int((size - 2 * inset) * 0.58)
    return [(left, top), (right, top), (right, taper_y), (cx, bot), (left, taper_y)]


def _make_shield_mask(size: int, inset: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).polygon(_shield_pts(size, inset), fill=255)
    return mask


def _noise_image(size: int) -> Image.Image:
    """Blurred random noise for rough edge texture."""
    data = bytes(random.randint(0, 255) for _ in range(size * size))
    img = Image.frombytes("L", (size, size), data)
    return img.filter(ImageFilter.GaussianBlur(2))


def apply_badge(
    path: pathlib.Path,
    *,
    border_color: tuple[int, int, int] = BADGE_COLOR_DEFAULT,
    target_size: int = BADGE_SIZE_DEFAULT,
    border_width: int = BADGE_WIDTH_DEFAULT,
) -> None:
    """Post-process a raw generated image into a shield-shaped badge in place."""
    img = Image.open(path).convert("RGBA")

    # Square crop from center
    s = min(img.size)
    left = (img.width - s) // 2
    top  = (img.height - s) // 2
    img  = img.crop((left, top, left + s, top + s))
    img  = img.resize((target_size, target_size), Image.LANCZOS)

    sz           = target_size
    outer_inset  = BADGE_MARGIN
    inner_inset  = BADGE_MARGIN + border_width

    outer_mask = _make_shield_mask(sz, outer_inset)
    inner_mask = _make_shield_mask(sz, inner_inset)

    # Ring = outer area minus inner cutout
    ring = ImageChops.subtract(outer_mask, inner_mask)

    # Rough outer edge: erode the outer mask to find the fringe, then noise-gate it
    fringe_kernel = BADGE_FRINGE * 2 + 1
    outer_eroded  = outer_mask.filter(ImageFilter.MinFilter(fringe_kernel))
    outer_fringe  = ImageChops.subtract(outer_mask, outer_eroded)
    rough_fringe  = ImageChops.multiply(outer_fringe, _noise_image(sz))
    rough_fringe  = rough_fringe.point(lambda x: 255 if x > 80 else 0)

    # Final ring: solid eroded center + rough outer fringe (clipped to ring area)
    solid_ring = ImageChops.subtract(outer_eroded, inner_mask)
    final_ring = ImageChops.add(solid_ring, rough_fringe)

    # Composite onto transparent canvas
    result = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    result.paste(img, mask=inner_mask)                                   # image inside shield
    border_layer = Image.new("RGBA", (sz, sz), (*border_color, 255))
    result.paste(border_layer, mask=final_ring)                          # amber ring on top

    result.save(path)


def parse_frontmatter(path: pathlib.Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    try:
        end = text.index("---", 3)
    except ValueError:
        return {}
    return yaml.safe_load(text[3:end]) or {}


def load_campaign_prefix(campaign_root: pathlib.Path) -> str:
    config = campaign_root / "campaign.yaml"
    if not config.exists():
        return ""
    data = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    return (data.get("image_prompt_prefix") or "").strip()


def collect_image_prompts(md_path: pathlib.Path) -> tuple[list[str], str]:
    """Resolve image prompts from frontmatter, else HTML comments (session pages only)."""
    fm = parse_frontmatter(md_path)
    prefix = (fm.get("image_prompt_prefix") or "").strip()
    raw = fm.get("image_prompt")
    if raw:
        items = raw if isinstance(raw, list) else [raw]
        prompts = [str(p).strip() for p in items if str(p).strip()]
        return prompts, prefix

    if "sessions" not in md_path.parts:
        return [], prefix

    text = md_path.read_text(encoding="utf-8")
    found = re.findall(r"<!--\s*image_prompt:\s*(.+?)\s*-->", text)
    prompts = [p.strip() for p in found if p.strip()]
    return prompts, prefix


def badge_kwargs_from_hex(
    hex_color: str,
    *,
    size: int = BADGE_SIZE_DEFAULT,
    width: int = BADGE_WIDTH_DEFAULT,
) -> dict:
    h = hex_color.lstrip("#")
    border_color = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
    return {"border_color": border_color, "target_size": size, "border_width": width}


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


def generate_one(
    client,
    prompt: str,
    out_path: pathlib.Path,
    model: str,
    force: bool = False,
    badge_opts: dict | None = None,
) -> bool:
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

    if badge_opts is not None:
        print(f"  badging: {out_path.name}")
        apply_badge(out_path, **badge_opts)

    return True


def badge_existing_file(md_path: pathlib.Path, badge_opts: dict, campaign_root: pathlib.Path) -> int:
    """Apply badge post-processing to already-generated images for a markdown file."""
    prompts, _ = collect_image_prompts(md_path)
    if not prompts:
        return 0

    paths = output_paths(md_path, len(prompts))

    print(f"\n{md_path.relative_to(campaign_root)}  ({len(paths)} image(s))")
    badged = 0
    for p in paths:
        if not p.exists():
            print(f"  skip (missing): {p.name}")
            continue
        print(f"  badging: {p.name}")
        apply_badge(p, **badge_opts)
        badged += 1
    return badged


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
    badge_opts: dict | None = None,
    campaign_root: pathlib.Path | None = None,
) -> int:
    """Process one markdown file. Returns number of images generated."""
    root = campaign_root or campaign_root_from_env()

    prompts, file_prefix = collect_image_prompts(md_path)
    if not prompts:
        return 0

    paths = output_paths(md_path, len(prompts))

    if image_index is not None:
        idx = image_index - 1
        if idx < 0 or idx >= len(prompts):
            print(f"  error: --image {image_index} is out of range (file has {len(prompts)} prompt(s))")
            return 0
        prompts = [prompts[idx]]
        paths = [paths[idx]]

    print(f"\n{md_path.relative_to(root)}  ({len(prompts)} prompt(s))")

    generated = 0
    for i, (per_image, out_path) in enumerate(zip(prompts, paths)):
        if i > 0:
            time.sleep(delay)
        final_prompt = build_prompt(per_image, cli_prefix, campaign_prefix, file_prefix, prompt_override)
        if generate_one(client, final_prompt, out_path, model, force=force, badge_opts=badge_opts):
            generated += 1

    return generated


def generate_session_images(
    *,
    campaign_dir: pathlib.Path,
    session_date_str: str,
    model: str = "imagen-4.0-fast-generate-001",
    delay: float = 6.0,
    force: bool = False,
    badge: bool = False,
    badge_color_hex: str = "d2a032",
    badge_size: int = BADGE_SIZE_DEFAULT,
    badge_width: int = BADGE_WIDTH_DEFAULT,
    api_key: str | None = None,
) -> int:
    """Generate achievement imagery for ``public/sessions/YYYY-MM-DD.md`` — same filenames as CLI."""
    campaign_dir = campaign_dir.resolve()
    session_md = campaign_dir / "public" / "sessions" / f"{session_date_str}.md"
    if not session_md.exists():
        raise FileNotFoundError(f"Session page not found: {session_md}")

    prompts, _ = collect_image_prompts(session_md)
    if not prompts:
        print("No image prompts found in session page.")
        print('Use YAML image_prompt in frontmatter, or legacy HTML comments:')
        print('  <!-- image_prompt: bold vintage woodcut... -->')
        return 0

    key = api_key if api_key is not None else os.environ.get("GOOGLE_KEY", "")
    if not key:
        raise ValueError("GOOGLE_KEY missing (env or scrollcase/.env)")

    client = genai.Client(api_key=key)
    campaign_prefix = load_campaign_prefix(campaign_dir)
    badge_opts = (
        badge_kwargs_from_hex(badge_color_hex, size=badge_size, width=badge_width) if badge else None
    )
    return process_file(
        session_md,
        client,
        model,
        delay,
        force=force,
        campaign_prefix=campaign_prefix,
        campaign_root=campaign_dir,
        badge_opts=badge_opts,
    )


def main():
    parser = argparse.ArgumentParser(description="Generate campaign artwork")
    parser.add_argument("files", nargs="*", metavar="FILE",
                        help="Markdown file(s) to process")
    parser.add_argument("--scan", choices=("characters", "npcs", "locations", "sessions"), metavar="TYPE",
                        help="Scan all .md files in a wiki directory")
    parser.add_argument("--prompt", metavar="TEXT",
                        help="One-off mode: full image prompt (no prefix layering applied)")
    parser.add_argument("--name", metavar="NAME",
                        help="One-off mode: output filename without extension (required with --prompt)")
    parser.add_argument("--type", choices=("characters", "npcs", "locations", "other"), default="other", dest="img_type",
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
    parser.add_argument("--badge", action="store_true",
                        help="Post-process each generated image into a shield-shaped badge")
    parser.add_argument("--badge-only", action="store_true", dest="badge_only",
                        help="Apply badge post-processing to existing images without regenerating")
    parser.add_argument("--badge-size", type=int, default=BADGE_SIZE_DEFAULT, metavar="PX",
                        help=f"Badge output size in pixels (default: {BADGE_SIZE_DEFAULT})")
    parser.add_argument("--badge-width", type=int, default=BADGE_WIDTH_DEFAULT, metavar="PX",
                        help=f"Border ring width in pixels at output size (default: {BADGE_WIDTH_DEFAULT})")
    parser.add_argument("--badge-color", default="d2a032", metavar="RRGGBB",
                        help="Border color as hex (default: d2a032, warm amber)")
    args = parser.parse_args()

    if args.prompt and not args.name:
        parser.error("--prompt requires --name")
    if args.image_index is not None and (args.scan or len(args.files) != 1):
        parser.error("--image requires exactly one FILE argument (not --scan or multiple files)")
    if args.badge_only and args.prompt:
        parser.error("--badge-only cannot be used with --prompt")
    if not args.prompt and not args.files and not args.scan:
        parser.error("Provide FILE(s), --scan TYPE, or --prompt TEXT --name NAME")

    campaign_root = campaign_root_from_env()
    scan_directories = scan_dirs(campaign_root)
    type_directories = type_dirs(campaign_root)

    badge_opts = badge_kwargs_from_hex(
        args.badge_color, size=args.badge_size, width=args.badge_width
    )

    if args.badge_only:
        md_files: list[pathlib.Path] = []
        if args.scan:
            md_files.extend(sorted(scan_directories[args.scan].glob("*.md")))
        for f in args.files:
            p = pathlib.Path(f)
            if not p.is_absolute():
                p = campaign_root / p
            md_files.append(p.resolve())

        total = sum(badge_existing_file(md_path, badge_opts, campaign_root) for md_path in md_files)
        print(f"\nDone. {total} image(s) badged.")
        return

    badge_opts_for_gen = badge_opts if args.badge else None

    campaign_prefix = load_campaign_prefix(campaign_root)
    client = genai.Client(api_key=os.environ["GOOGLE_KEY"])
    total = 0

    if args.prompt:
        out_path = type_directories[args.img_type] / f"{args.name}.png"
        print(f"\none-off: {args.name} ({args.img_type})")
        if generate_one(client, args.prompt, out_path, args.model, force=args.force, badge_opts=badge_opts_for_gen):
            total += 1
    else:
        md_files: list[pathlib.Path] = []
        if args.scan:
            md_files.extend(sorted(scan_directories[args.scan].glob("*.md")))
        for f in args.files:
            p = pathlib.Path(f)
            if not p.is_absolute():
                p = campaign_root / p
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
                badge_opts=badge_opts_for_gen,
                campaign_root=campaign_root,
            )

    print(f"\nDone. {total} image(s) generated.")


if __name__ == "__main__":
    main()

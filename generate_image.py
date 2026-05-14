#!/usr/bin/env python3
"""Generate a campaign image (character portrait or other asset) in the pulp adventure style."""
import os
import argparse
import pathlib
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).parent / ".env")

from google import genai
from google.genai import types

STYLE_PREFIX = (
    "1930s pulp adventure paperback illustration style, bold linework, "
    "limited color palette of deep blues and slate grays with stark white snow, "
    "flat simplified background, dramatic lighting, "
    "arctic Icewind Dale setting with snow and ice always present, "
    "absolutely no text, no letters, no words, no labels anywhere in the image — "
)

CAMPAIGN_DIR = (pathlib.Path(__file__).parent / os.environ["CAMPAIGN_DIR"]).resolve()

TYPE_DIRS = {
    "pc":       CAMPAIGN_DIR / "public" / "characters" / "pcs" / "images",
    "npc":      CAMPAIGN_DIR / "public" / "npcs" / "images",
    "location": CAMPAIGN_DIR / "public" / "locations" / "images",
    "other":    CAMPAIGN_DIR / "public" / "images",
}


def main():
    parser = argparse.ArgumentParser(description="Generate a campaign image in pulp adventure style")
    parser.add_argument("--type", choices=TYPE_DIRS.keys(), default="other",
                        help="Image type determines output directory")
    parser.add_argument("--name", required=True,
                        help="Output filename (without extension)")
    parser.add_argument("--desc", required=True,
                        help="Character/subject description to append to the style prefix")
    parser.add_argument("--model", default="imagen-4.0-fast-generate-001",
                        help="Imagen model to use")
    parser.add_argument("--no-prefix", action="store_true",
                        help="Skip the standard style prefix and use --desc as the full prompt")
    args = parser.parse_args()

    prompt = args.desc if args.no_prefix else STYLE_PREFIX + args.desc

    out_dir = TYPE_DIRS[args.type]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.name}.png"

    client = genai.Client(api_key=os.environ["GOOGLE_KEY"])

    print(f"Generating: {args.name} ({args.type})")
    print(f"Prompt: {prompt[:120]}...")
    response = client.models.generate_images(
        model=args.model,
        prompt=prompt,
        config=types.GenerateImagesConfig(number_of_images=1),
    )
    response.generated_images[0].image.save(out_path)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()

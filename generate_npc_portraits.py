#!/usr/bin/env python3
"""Generate NPC portraits using Google Imagen."""
import os
import pathlib
import time
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).parent / ".env")

from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GOOGLE_KEY"])

CAMPAIGN_DIR = (pathlib.Path(__file__).parent / os.environ["CAMPAIGN_DIR"]).resolve()

npcs = [
    (
        "pasha",
        "Pasha, a human woman warrior and wilderness guide, weathered face with determined eyes, "
        "practical cold-weather armor and furs, carrying a weapon, experienced and tough, "
        "Icewind Dale arctic setting, D&D character portrait, painterly style, dramatic lighting, no text",
    ),
    (
        "sook",
        "Sook, a young Goliath hunter, grey-blue mottled skin, tall and lean, "
        "hunter's furs and leather, carries a large bow, scar visible on his right hand, "
        "quiet watchful expression, Icewind Dale arctic setting, D&D character portrait, painterly style, no text",
    ),
    (
        "old-goat",
        "Old Goat, an elderly female Goliath chieftain, deeply lined face full of wisdom and authority, "
        "grey-blue mottled skin, smoking a pipe, tribal elder's clothing and furs, "
        "sharp piercing eyes that miss nothing, Icewind Dale arctic setting, D&D character portrait, painterly style, no text",
    ),
    (
        "kaskur",
        "Kaskur, a massive imposing Goliath hunter, grey-blue mottled skin, "
        "enormous longbow slung across his chest, hatchets at his belt, "
        "stone-faced expression of deep skepticism, cold weather furs and armor, "
        "Icewind Dale arctic setting, D&D character portrait, painterly style, dramatic lighting, no text",
    ),
]

out_dir = CAMPAIGN_DIR / "wiki" / "characters" / "npcs" / "images"
out_dir.mkdir(parents=True, exist_ok=True)

for i, (name, prompt) in enumerate(npcs):
    if i > 0:
        time.sleep(10)
    print(f"Generating portrait for {name}...")
    response = client.models.generate_images(
        model="imagen-4.0-fast-generate-001",
        prompt=prompt,
        config=types.GenerateImagesConfig(number_of_images=1),
    )
    out_path = out_dir / f"{name}.png"
    response.generated_images[0].image.save(out_path)
    print(f"  Saved {out_path}")

print("Done.")

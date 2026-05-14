#!/usr/bin/env python3
"""Generate character portraits using Google Imagen."""
import os
import pathlib
import time
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).parent / ".env")

from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GOOGLE_KEY"])

CAMPAIGN_DIR = (pathlib.Path(__file__).parent / os.environ["CAMPAIGN_DIR"]).resolve()

characters = [
    (
        "alina",
        "Alina Shandorath, a Tiefling wizard, purple-tinged skin, small curved horns, "
        "wearing practical traveler's clothes, carrying a cartographer's satchel, "
        "intelligent piercing eyes, fantasy D&D character portrait, painterly style, "
        "dramatic lighting, no text",
    ),
    (
        "dr-medicine",
        "Doctor Medicine, a confident human warlock in fine clothes and a costume, "
        "theatrical bearing, warm smile that doesn't quite reach his eyes, "
        "carries a rod, D&D character portrait, painterly style, dramatic lighting, no text",
    ),
    (
        "river",
        "Roaring River, a Tabaxi, cat-like humanoid with spotted fur, "
        "fluid athletic stance, leather armor, dual rapiers, "
        "D&D character portrait, painterly style, dramatic lighting, no text",
    ),
    (
        "berg",
        "Berg Wurdnowwah, a large muscular Orc fighter, weathered soldier's face, "
        "chain mail armor, pike weapon, steady confident expression, "
        "D&D character portrait, painterly style, dramatic lighting, no text",
    ),
]

out_dir = CAMPAIGN_DIR / "wiki" / "characters" / "pcs" / "images"
out_dir.mkdir(parents=True, exist_ok=True)

for i, (name, prompt) in enumerate(characters):
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

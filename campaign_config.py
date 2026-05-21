"""Campaign settings helpers shared by scrollcase scripts."""
from __future__ import annotations

import pathlib
import shutil

_PACKAGE_DIR = pathlib.Path(__file__).resolve().parent
BUNDLED_DEFAULT_PORTRAIT = _PACKAGE_DIR / "assets" / "default-portrait.png"
DEFAULT_PORTRAIT_FILENAME = "default-portrait.png"


def default_portrait_url(campaign_dir: pathlib.Path, campaign: dict) -> str:
    """Site-root URL for the campaign's generic portrait."""
    custom = (campaign.get("default_portrait") or "").strip()
    if custom:
        return custom
    slug = (campaign.get("slug") or campaign_dir.name).strip()
    return f"/rpg/{slug}/public/images/{DEFAULT_PORTRAIT_FILENAME}"


def resolve_portrait_url(
    campaign_dir: pathlib.Path,
    campaign: dict,
    image: str | None,
) -> str:
    """Character/NPC image, or the campaign generic portrait when missing."""
    if image and str(image).strip():
        return str(image).strip()
    return default_portrait_url(campaign_dir, campaign)


def campaign_default_portrait_path(campaign_dir: pathlib.Path) -> pathlib.Path:
    return campaign_dir / "public" / "images" / DEFAULT_PORTRAIT_FILENAME


def ensure_campaign_default_portrait_file(campaign_dir: pathlib.Path, campaign: dict) -> pathlib.Path | None:
    """Copy scrollcase's bundled PNG into the campaign if no custom URL and file is missing."""
    if (campaign.get("default_portrait") or "").strip():
        return None
    dest = campaign_default_portrait_path(campaign_dir)
    if dest.exists():
        return dest
    if not BUNDLED_DEFAULT_PORTRAIT.is_file():
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BUNDLED_DEFAULT_PORTRAIT, dest)
    return dest

"""
Thin wrapper around ddb-proxy (https://github.com/MrPrimate/ddb-proxy).
Reads COBALT_COOKIE and optionally DDB_PROXY_URL from .env.

Without DDB_PROXY_URL the client tries the proxy on blueglow first, then
localhost, and uses the first one that answers /ping. DDB_PROXY_URL may be a
single URL (used as-is) or a comma-separated list (tried in order).
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

_DEFAULT_PROXY_URLS = ("http://blueglow:3000", "http://localhost:3000")
_PING_TIMEOUT = 3


def _candidate_urls(proxy_url: str | None) -> list[str]:
    raw = proxy_url or os.getenv("DDB_PROXY_URL")
    if raw:
        urls = [u.strip() for u in raw.split(",") if u.strip()]
    else:
        urls = list(_DEFAULT_PROXY_URLS)
    return [u.rstrip("/") for u in urls]


def find_proxy_url(candidates: list[str]) -> str:
    """Return the first candidate whose /ping answers; raise if none do."""
    for url in candidates:
        try:
            if requests.get(f"{url}/ping", timeout=_PING_TIMEOUT).ok:
                return url
        except requests.RequestException:
            continue
    raise ConnectionError(
        "No ddb-proxy answered /ping at: " + ", ".join(candidates)
    )


class DDBClient:
    def __init__(
        self,
        cobalt_token: str | None = None,
        proxy_url: str | None = None,
    ):
        self.cobalt = cobalt_token or os.getenv("COBALT_COOKIE")
        if not self.cobalt:
            raise ValueError(
                "Cobalt token required: set COBALT_COOKIE in .env or pass cobalt_token="
            )
        candidates = _candidate_urls(proxy_url)
        self.proxy_url = (
            candidates[0] if len(candidates) == 1 else find_proxy_url(candidates)
        )

    def _post(self, path: str, data: dict | None = None) -> dict:
        payload = {"cobalt": self.cobalt, **(data or {})}
        response = requests.post(
            f"{self.proxy_url}{path}", json=payload, timeout=30
        )
        response.raise_for_status()
        return response.json()

    def auth(self) -> dict:
        """Validate the cobalt token. Returns {success: bool, message: str}."""
        return self._post("/proxy/auth")

    def get_character(
        self, character_id: str | int, update_id: str | None = None
    ) -> dict:
        """Full parsed character sheet including spells, items, features, modifiers."""
        data: dict = {"characterId": str(character_id)}
        if update_id:
            data["updateId"] = update_id
        return self._post("/proxy/character", data)

    def get_campaigns(self) -> dict:
        """Campaigns available to the authenticated account."""
        return self._post("/proxy/campaigns")

    def get_items(self, campaign_id: str | int | None = None) -> dict:
        """Items available to the account or a specific campaign."""
        data: dict = {}
        if campaign_id:
            data["campaignId"] = str(campaign_id)
        return self._post("/proxy/items", data)

    def search_monsters(
        self,
        search_term: str,
        *,
        homebrew: bool = False,
        homebrew_only: bool = False,
        sources: list[int] | None = None,
        exact_match: bool = False,
    ) -> dict:
        """Search monsters by name. Returns up to 100 results per call."""
        data: dict = {
            "searchTerm": search_term,
            "homebrew": homebrew,
            "homebrewOnly": homebrew_only,
            "exactMatch": exact_match,
        }
        if sources:
            data["sources"] = sources
        return self._post("/proxy/monster", data)

    def get_monsters_by_id(self, ids: list[int]) -> dict:
        """Fetch full monster data for a list of DDB monster IDs."""
        return self._post("/proxy/monstersById", {"ids": ids})

    def get_class_spells(
        self, class_name: str, campaign_id: str | int | None = None
    ) -> dict:
        """Spell list for a class, filtered by level and access."""
        data: dict = {"className": class_name}
        if campaign_id:
            data["campaignId"] = str(campaign_id)
        return self._post("/proxy/class/spells", data)

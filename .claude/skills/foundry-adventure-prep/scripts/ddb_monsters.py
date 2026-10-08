"""Find the stock stat block a module creature reskins, and its 2024 replacement.

Early AL modules often rename a stock block and tweak one or two things (a
"Winged Kobold (Urd) Spy" is the Spy made Small, winged, and kobold). Compare
the module's stats against DDB's, then build the 2024 conversion from the
2024 base plus the module's changes.

Needs ddb-proxy running on blueglow or locally (DDBClient tries
http://blueglow:3000 first, then http://localhost:3000) and
COBALT_COOKIE in scrollcase's .env. Run with scrollcase's environment:

    uv run --project C:\\Users\\decha\\dev\\scrollcase python ddb_monsters.py search Spy Scout Kobold
    uv run --project C:\\Users\\decha\\dev\\scrollcase python ddb_monsters.py show 5195217 17021

search: one line per DDB monster whose name contains a term: id, source,
        legacy flag, AC, HP, and the six ability scores to compare.
show:   full blocks (traits, actions, bonus actions, reactions) as plain text.

Source ids seen so far: 1 Basic Rules (2014), 5 Monster Manual (2014),
14 Tales from the Yawning Portal, 15 Volo's, 85 Monsters of the Multiverse,
147 Monster Manual (2024).
"""

import html
import os
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, os.getenv("SCROLLCASE_DIR", str(Path.home() / "dev" / "scrollcase")))
from ddb_client import DDBClient  # noqa: E402


def _sources(client: DDBClient) -> dict[int, str]:
    cfg = requests.get(f"{client.proxy_url}/proxy/api/config/json", timeout=30).json()

    def find(o):
        if isinstance(o, dict):
            if isinstance(o.get("sources"), list):
                return o["sources"]
            for v in o.values():
                if r := find(v):
                    return r
        return None

    return {s["id"]: s.get("description") or s.get("name") for s in find(cfg) or []}


def _plain(h: str | None) -> str:
    h = re.sub(r"</p>\s*", "\n", h or "")
    return html.unescape(re.sub(r"<[^>]+>", "", h)).strip()


def _line(m: dict, srcs: dict[int, str]) -> str:
    stats = [s["value"] for s in m["stats"]]
    return (f'{m["name"]:<32} id={m["id"]:<8} {srcs.get(m["sourceId"], m["sourceId"])!s:<40.40} '
            f'legacy={m.get("isLegacy")!s:<5} AC {m["armorClass"]} '
            f'HP {m["averageHitPoints"]} ({m["hitPointDice"]["diceString"]}) {stats}')


def search(client: DDBClient, terms: list[str]) -> None:
    srcs, seen = _sources(client), set()
    for term in terms:
        for m in client.search_monsters(term).get("data", []):
            if m["id"] not in seen and term.lower() in m["name"].lower():
                seen.add(m["id"])
                print(_line(m, srcs))


def show(client: DDBClient, ids: list[int]) -> None:
    srcs = _sources(client)
    for m in client.get_monsters_by_id(ids).get("data", []):
        print(f"\n##### {_line(m, srcs)}")
        speeds = ", ".join(f'{x["movementId"]}:{x["speed"]}' for x in m["movements"])
        print(f'speed (1 walk, 3 climb, 4 fly, 5 swim) {speeds} | init {m.get("initiativeBonus")} | '
              f'skills {_plain(m.get("skillsHtml"))} | senses {_plain(m.get("sensesHtml"))}')
        for key in ("specialTraitsDescription", "actionsDescription",
                    "bonusActionsDescription", "reactionsDescription"):
            if m.get(key):
                print(f"-- {key.removesuffix('Description')}\n{_plain(m[key])}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "search":
        search(DDBClient(), args[1:])
    elif len(args) >= 2 and args[0] == "show":
        show(DDBClient(), [int(a) for a in args[1:]])
    else:
        sys.exit(__doc__)

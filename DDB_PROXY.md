# D&D Beyond Proxy — Reference Notes

ddb-proxy is a local Node.js service that authenticates against D&D Beyond's
internal APIs using your session cookie (the "Cobalt token") and proxies data
back as JSON. It was written for Foundry VTT but is a plain HTTP API usable
from any client.

Repo: https://github.com/MrPrimate/ddb-proxy  
Local path: `~/dev/ddb-proxy`

## Starting the proxy

```powershell
cd ~/dev/ddb-proxy
node index.js        # runs on http://localhost:3000
```

Verify it's up: `curl http://localhost:3000/ping` → `pong`

## The Cobalt Token

The proxy authenticates using the value of the `CobaltSession` cookie from a
logged-in D&D Beyond browser session. DDB signs you out periodically; when
that happens you need to refresh the value in `.env`.

**Canonical location:** `scrollcase/.env` as `COBALT_COOKIE=<value>`

The `ddb-proxy/.env` file was the original home for this; that's now redundant
and can be ignored.

### Getting the token quickly — bookmarklet

Create a bookmark in your browser with this as the URL. When on any
dndbeyond.com page while logged in, click it to copy your token to the
clipboard.

```
javascript:(function(){var m=document.cookie.match(/CobaltSession=([^;]+)/);if(m){navigator.clipboard.writeText(m[1]).then(function(){var d=document.createElement('div');d.style='position:fixed;top:20px;right:20px;background:#4CAF50;color:#fff;padding:12px 20px;border-radius:6px;font-family:sans-serif;font-size:14px;z-index:99999;box-shadow:0 2px 8px rgba(0,0,0,0.3)';d.textContent='✓ Cobalt token copied!';document.body.appendChild(d);setTimeout(function(){d.remove()},3000)})}else{alert('CobaltSession not readable (HttpOnly cookie).\nFallback: DevTools > Application > Cookies > dndbeyond.com > CobaltSession')}})()
```

> **Note:** If DDB has made `CobaltSession` an HttpOnly cookie (meaning
> JavaScript can't read it), the bookmarklet will show the fallback message.
> In that case use the DevTools snippet below instead.

### Fallback — DevTools Snippet (save once, run anytime)

In Chrome or Edge:  
F12 → Sources tab → Snippets (left sidebar) → New snippet → paste this → save.

```javascript
// Run on any dndbeyond.com page while logged in.
// Opens Application > Cookies automatically and copies the value.
const allCookies = document.cookie;
const match = allCookies.match(/CobaltSession=([^;]+)/);
if (match) {
  copy(match[1]);
  console.log('%c✓ Cobalt token copied to clipboard', 'color:green;font-weight:bold');
  console.log(match[1]);
} else {
  console.warn('CobaltSession not found in document.cookie (may be HttpOnly).');
  console.log('Manual path: DevTools → Application → Cookies → https://www.dndbeyond.com → CobaltSession');
}
```

To run a saved snippet: Ctrl+P in DevTools → type `!` → select the snippet name → Enter.

## Python client

`scrollcase/ddb_client.py` wraps all proxy endpoints. It reads `COBALT_COOKIE`
and optionally `DDB_PROXY_URL` from `.env`.

```python
from ddb_client import DDBClient

client = DDBClient()           # reads COBALT_COOKIE from .env
client.auth()                  # verify token is valid

client.get_character("12345678")
client.get_campaigns()
client.get_items(campaign_id="9999")
client.search_monsters("Remorhaz")
client.get_monsters_by_id([123, 456])
client.get_class_spells("Wizard")
```

The proxy must be running (`node index.js` in `~/dev/ddb-proxy`) before any
call is made. The client raises `requests.HTTPError` on non-2xx responses.

## Endpoints summary

| Endpoint | Method | Key params | Returns |
|---|---|---|---|
| `/ping` | GET | — | `"pong"` |
| `/proxy/auth` | POST | cobalt | `{success, message}` |
| `/proxy/character` | POST | characterId | Full character sheet |
| `/proxy/campaigns` | POST | — | Your campaigns |
| `/proxy/items` | POST | campaignId? | Available items |
| `/proxy/monster` | POST | searchTerm, homebrew, sources | Monster search (100/page) |
| `/proxy/monstersById` | POST | ids[] | Monster details by ID |
| `/proxy/class/spells` | POST | className, campaignId? | Spell list for class |
| `/proxy/api/config/json` | GET | — | DDB config / source list |

## Planned integrations

### scrollcase → wiki (hoshisabi.github.io/rpg)

When processing a session, resolve item reward names to DDB IDs and URLs so
the public session file gets structured frontmatter:

```yaml
rewards:
  - name: Wand of Magic Missiles
    ddb_id: 4764
    ddb_url: https://www.dndbeyond.com/magic-items/4764-wand-of-magic-missiles
```

Character pages in `public/characters/` would be regenerated from
`get_character()` each session rather than maintained by hand.

### al_adventures → markdown2pdf

Replace the HTML-scraping `ddb_to_md.py` with API-based fetching using
`search_monsters()` / `get_monsters_by_id()`. The manuscript references a
monster by name, the build step fetches and formats the stat block in the
blockquote format the Pandoc pipeline already understands.

DM's Guild / DungeonCraft license permits full stat block reproduction —
no need to truncate to SRD-only content.

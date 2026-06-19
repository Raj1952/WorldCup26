"""
Download WC2026 team flag SVGs from lipis/flag-icons (MIT licence, public-domain art).
Saves to assets/flags/{code}.svg.  Safe to re-run — skips already-downloaded files.
"""
import sys, time
from pathlib import Path
from urllib.request import urlretrieve, Request
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE = "https://raw.githubusercontent.com/lipis/flag-icons/main/flags/4x3/{code}.svg"
OUT  = Path("assets/flags")
OUT.mkdir(parents=True, exist_ok=True)

# ALL 48 WC2026 teams + subdivision flags
CODES = [
    # Standard ISO alpha-2
    "dz","ar","au","at","be","ba","br","ca","cv","co",
    "hr","cw","cz","cd","ec","eg","fr","de","gh","ht",
    "ir","iq","ci","jp","jo","mx","ma","nl","nz","no",
    "pa","py","pt","qa","sa","sn","za","kr","es","se",
    "ch","tn","tr","us","uy","uz",
    # UK subdivision flags (NOT the Union Jack)
    "gb-eng","gb-sct","gb-wls",
]

ok = skip = fail = 0
for code in CODES:
    dest = OUT / f"{code}.svg"
    if dest.exists():
        skip += 1
        continue
    url = BASE.format(code=code)
    try:
        urlretrieve(url, dest)
        ok += 1
        time.sleep(0.05)   # polite rate limit
    except HTTPError as e:
        print(f"  FAIL {code}: {e}")
        fail += 1

print(f"Downloaded {ok}  |  Skipped {skip}  |  Failed {fail}")
print(f"Assets in: {OUT.resolve()}")

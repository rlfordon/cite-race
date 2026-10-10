"""Notoriety of Supreme Court cases from Wikipedia: which decisions have an English article, and how often it is read.

Step 1 (done by hand once; rerun to refresh): Wikidata query for every item that is an instance of
"United States Supreme Court decision" (Q19692072) with an enwiki sitelink -> data/notoriety/wikidata.csv
(item, label, article, legal citation P1031, publication date P577).

Step 2 (this script, --views): fetch monthly user pageviews for every article over the last 12 full months
from the Wikimedia REST API -> data/notoriety/pageviews.json  {article_title: views}.

Step 3 (this script, --map): join the articles to graph nodes (U.S. cite, else S. Ct. cite, else name+year)
and write docs/data/notable.json  { "built", "window", "cases": [[cl_id, views, article_title], ...] sorted by views desc }.

  python scripts/notoriety.py --views          # ~3,200 requests, about a minute at 8 workers
  python scripts/notoriety.py --map
"""
import argparse, csv, json, os, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTO = os.path.join(ROOT, "data", "notoriety")
UA = "cite-race-notoriety/0.1 (https://github.com/rlfordon/cite-race)"


def log(m): print(m, file=sys.stderr, flush=True)


def wikidata_rows():
    return list(csv.DictReader(open(os.path.join(NOTO, "wikidata.csv"), encoding="utf-8")))


def window():
    """Last 12 full months, as (start, end) YYYYMMDD strings for the pageviews API."""
    today = date.today()
    end_y, end_m = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    start_y, start_m = (end_y - 1, end_m + 1) if end_m < 12 else (end_y, 1)
    return f"{start_y}{start_m:02d}0100", f"{end_y}{end_m:02d}2800"


def fetch_views(title, start, end):
    url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
           f"{urllib.parse.quote(title, safe='')}/monthly/{start}/{end}")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                return sum(i["views"] for i in json.load(r).get("items", []))
        except urllib.error.HTTPError as e:
            if e.code == 404: return 0
            time.sleep(2 * (attempt + 1))  # 429 and the occasional 5xx: back off and retry
        except Exception:
            time.sleep(1 + attempt)
    return None


def do_views(workers):
    path = os.path.join(NOTO, "pageviews.json")
    cache = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    start, end = window()
    titles = sorted({urllib.parse.unquote(r["article"].rsplit("/", 1)[1]) for r in wikidata_rows()})
    todo = [t for t in titles if t not in cache]
    log(f"{len(titles)} articles, {len(todo)} to fetch, window {start[:6]}-{end[:6]}")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for k, (t, v) in enumerate(zip(todo, ex.map(lambda t: fetch_views(t, start, end), todo)), 1):
            if v is not None: cache[t] = v
            if k % 200 == 0:
                log(f"  {k}/{len(todo)} ({time.time() - t0:.0f}s)"); json.dump(cache, open(path, "w", encoding="utf-8"))
    json.dump(cache, open(path, "w", encoding="utf-8"))
    json.dump({"window": [start[:6], end[:6]]}, open(os.path.join(NOTO, "window.json"), "w"))
    log(f"wrote {path}: {len(cache)} articles, {sum(1 for t in todo if cache.get(t) is None)} failed")


ABBREV = {"comm'n": "commission", "ass'n": "association", "assn": "association", "dept": "department", "dep't": "department",
          "bd": "board", "nat'l": "national", "natl": "national", "ins": "insurance", "r.r.": "railroad", "ry": "railway",
          "sch": "school", "dist": "district", "cty": "county", "univ": "university", "mfg": "manufacturing"}


def norm_name(s):
    s = s.lower().replace("&", "and")
    for a, b in ABBREV.items():
        s = re.sub(r"" + re.escape(a) + r"\.?(?=\s|$|,)", b, s)
    s = re.sub(r"\b(inc|co|corp|ltd|llc|the|of|et al|ex rel|on behalf of)\b\.?", " ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return " ".join(w for w in s.split() if w not in {"v", "vs"})


def do_map():
    g = json.load(open(os.path.join(ROOT, "docs", "data", "graph.json"), encoding="utf-8"))
    views = json.load(open(os.path.join(NOTO, "pageviews.json"), encoding="utf-8"))
    win = json.load(open(os.path.join(NOTO, "window.json")))["window"]
    by_cite = {}
    for i, c in enumerate(g["cites"]):
        if c and g["real"][i]: by_cite.setdefault(c, i)
    by_name_year, by_name = {}, {}
    for i, (n, y) in enumerate(zip(g["names"], g["years"])):
        if g["real"][i]:
            by_name_year.setdefault((norm_name(n), y), i)
            by_name.setdefault(norm_name(n), []).append(i)
    items = {}
    for r in wikidata_rows():
        it = items.setdefault(r["item"], {"label": r["itemLabel"], "title": urllib.parse.unquote(r["article"].rsplit("/", 1)[1]),
                                           "cites": set(), "year": None})
        if r["cite"]: it["cites"].add(re.sub(r"\s+", " ", r["cite"]).replace("S.Ct.", "S. Ct."))
        if r["date"]: it["year"] = int(r["date"][:4])
    how = {"us": 0, "sct": 0, "name": 0, "none": 0}
    out = {}
    for it in items.values():
        node = None
        for c in it["cites"]:
            if re.match(r"^\d+ U\.S\. \d+$", c) and c in by_cite: node, how["us"] = by_cite[c], how["us"] + 1; break
        if node is None:
            for c in it["cites"]:
                if "S. Ct." in c and c in by_cite: node, how["sct"] = by_cite[c], how["sct"] + 1; break
        if node is None and it["year"]:
            for y in (it["year"], it["year"] - 1, it["year"] + 1):
                k = (norm_name(it["label"]), y)
                if k in by_name_year: node, how["name"] = by_name_year[k], how["name"] + 1; break
        if node is None and not it["year"] and norm_name(it["label"]) in by_name:
            # no citation and no date on Wikidata: the best-connected real node of that name
            node, how["name"] = max(by_name[norm_name(it["label"])], key=lambda i: g["cited_all"][i]), how["name"] + 1
        if node is None: how["none"] += 1; continue
        v = views.get(it["title"], 0)
        if node not in out or out[node][0] < v: out[node] = (v, it["title"])
    cases = sorted(([g["ids"][i], v, t] for i, (v, t) in out.items()), key=lambda x: -x[1])
    res = {"built": time.strftime("%Y-%m-%d"), "window": win, "source": "English Wikipedia pageviews (user, all access) via Wikidata Q19692072",
           "cases": cases}
    path = os.path.join(ROOT, "docs", "data", "notable.json")
    json.dump(res, open(path, "w", encoding="utf-8"), separators=(",", ":"))
    log(f"matched {len(out)} of {len(items)} articles ({how}); wrote {path}")
    for floor in (50000, 20000, 10000, 5000, 2000):
        log(f"  >= {floor:6} views/yr: {sum(1 for c in cases if c[1] >= floor)} cases")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", action="store_true"); ap.add_argument("--map", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    if a.views: do_views(a.workers)
    if a.map: do_map()
    if not (a.views or a.map): ap.print_help()

"""Precompute Jev's routes for every docket puzzle and a pool of random pairs.

Jev is TypeSafe's typed-judgment model (https://docs.typesafe.ai). At each hop it reads
the target's syllabus beside each case it could move to and scores how closely their
legal issues match; code takes the warmest. Rules the code enforces, not Jev: moves follow
the mode's direction, a visited case is never revisited, the target is taken whenever it
is one hop away, a dead end sends Jev back a case, and Jev gives up after --max-hops.

Output: docs/data/jev.json, which the game replays (app/static-api.js, scripts/serve.py).
  { "model", "built", "max_hops", "pool": {mode: ["<startcl>-<targetcl>", ...]},
    "routes": {"<mode>:<startcl>-<targetcl>": {"path": [cl, ...], "score": [x, ...], "reached": bool}} }
`score` is Jev's expected relatedness (0 to 4) for each hop; null for a hop to the target in reach.

Case text comes from the local CAP copy (data/cap/raw/<reporter>/<vol>.zip), falling back to
static.case.law. Jev's answers and the case summaries are cached under data/jev/, so a rerun
only asks what it has not asked before.

  pip install typesafe-sdk
  echo TYPESAFE_API_KEY=... > .env                                   # or set it in the environment; .env is git-ignored
  python scripts/precompute_jev.py                                   # starters + 20 random pairs per mode
  python scripts/precompute_jev.py --pool 50 --modes any --workers 6
  python scripts/precompute_jev.py --fake                            # no key: word-overlap stand-in, to test the plumbing
"""

import argparse
import html.parser
import json
import os
import random
import re
import sys
import threading
import time
import urllib.request
import zipfile
from collections import deque
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DATA = os.path.join(ROOT, "docs", "data")
CACHE_DIR = os.path.join(ROOT, "data", "jev")
ARCHIVE = "https://static.case.law"
MODES = ("any", "back", "forward")


def load_dotenv():
    """KEY=value lines from the repo's .env into the environment, without overriding what is already set."""
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))

QUESTION = ("Two U.S. Supreme Court cases, each given by name, year and the start of its syllabus. "
            "How closely related are the legal issues the two cases decide?")
LEVELS = [
    "Unrelated areas of law.",
    "Same broad field of law, different issues.",
    "Related doctrines; one could plausibly mention the other.",
    "Same doctrine or legal question, approached from different facts.",
    "Squarely the same legal question; one is likely a leading authority for the other.",
]


def log(msg):
    print(msg, file=sys.stderr, flush=True)


# ----------------------------------------------------------------------------- graph
class Graph:
    def __init__(self, path):
        g = json.load(open(path, encoding="utf-8"))
        self.ids, self.names, self.years = g["ids"], g["names"], g["years"]
        self.cited_all, self.real, self.text = g["cited_all"], g["real"], g["text"]
        self.n = len(self.ids)
        self.by_cl = {cl: i for i, cl in enumerate(self.ids)}
        self.out = [[] for _ in range(self.n)]   # i cites j
        self.inn = [[] for _ in range(self.n)]   # j is cited by i
        e = g["edges"]
        for k in range(0, len(e), 2):
            self.out[e[k]].append(e[k + 1])
            self.inn[e[k + 1]].append(e[k])
        self.und = [sorted(set(a) | set(b)) for a, b in zip(self.out, self.inn)]

    def neighbours(self, i, mode):
        return self.out[i] if mode == "back" else self.inn[i] if mode == "forward" else self.und[i]

    def bfs(self, start, mode, max_depth):
        dist = {start: 0}
        q = deque([start])
        while q:
            x = q.popleft()
            if dist[x] >= max_depth:
                continue
            for y in self.neighbours(x, mode):
                if y not in dist:
                    dist[y] = dist[x] + 1
                    q.append(y)
        return dist


# ----------------------------------------------------------------------------- case text
class _Syllabus(html.parser.HTMLParser):
    """Collects <p> text, noting whether each sits in the head matter and its class."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.paras, self.cur, self.skip = [], [], None, 0

    VOID = {"br", "img", "hr", "input", "meta", "link", "wbr", "col", "area", "base", "source"}

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            if tag == "br" and self.cur is not None:
                self.cur["text"].append(" ")
            return
        cls = (dict(attrs).get("class") or "").split()
        if tag in ("p", "blockquote") and self.cur is None:
            self.cur = {"cls": cls, "head": any("head-matter" in c for c in self.stack), "text": []}
        if "page-label" in cls:
            self.skip += 1
        self.stack.append(" ".join(cls) + (" page-label-open" if "page-label" in cls else ""))

    def handle_endtag(self, tag):
        if tag in self.VOID or not self.stack:
            return
        top = self.stack.pop()
        if top.endswith("page-label-open"):
            self.skip -= 1
        if tag in ("p", "blockquote") and self.cur is not None:
            t = re.sub(r"\s+", " ", "".join(self.cur["text"])).strip()
            if t:
                self.paras.append((self.cur["head"], self.cur["cls"], t))
            self.cur = None

    def handle_data(self, data):
        if self.cur is not None and not self.skip:
            self.cur["text"].append(data)


def summary_from_html(raw):
    """The syllabus, or the opening paragraphs when a volume has none (as the game's hover card does)."""
    p = _Syllabus()
    p.feed(raw)
    syl = [t for head, cls, t in p.paras if "syllabus" in cls or (head and "summary" in cls and len(t) >= 140)]
    if syl:
        return " ".join(syl[:4])
    body = [t for head, cls, t in p.paras if not head and len(t) > 60 and re.match(r"[A-Z“\"‘']", t)]
    return " ".join(body[:3])


class Texts:
    def __init__(self, graph, fetch):
        self.g, self.fetch = graph, fetch
        self.path = os.path.join(CACHE_DIR, "summaries.json")
        self.cache = json.load(open(self.path, encoding="utf-8")) if os.path.exists(self.path) else {}
        self.lock = threading.Lock()
        self.dirty = 0

    def raw_html(self, i):
        t = self.g.text[i]
        if not t:
            return ""
        rep, vol, member = t
        zpath = os.path.join(ROOT, "data", "cap", "raw", rep, f"{vol}.zip")
        if os.path.exists(zpath):
            with zipfile.ZipFile(zpath) as z:
                return z.read(f"html/{member}.html").decode("utf-8", "replace")
        if not self.fetch:
            return ""
        with urllib.request.urlopen(f"{ARCHIVE}/{rep}/{vol}/html/{member}.html", timeout=30) as r:
            return r.read().decode("utf-8", "replace")

    def summary(self, i):
        key = str(self.g.ids[i])
        with self.lock:
            if key in self.cache:
                return self.cache[key]
        try:
            s = summary_from_html(self.raw_html(i))
        except Exception as e:  # noqa: BLE001  (a missing text costs Jev context, not the run)
            log(f"  no text for {self.g.names[i]}: {e}")
            s = ""
        with self.lock:
            self.cache[key] = s
            self.dirty += 1
        return s

    def save(self):
        with self.lock:
            if self.dirty:
                os.makedirs(CACHE_DIR, exist_ok=True)
                json.dump(self.cache, open(self.path, "w", encoding="utf-8"))
                self.dirty = 0


# ----------------------------------------------------------------------------- Jev
def clip(s, n):
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + " ..."


class Judge:
    """Expected relatedness (0..4) of a candidate to the target, cached per (target, candidate)."""

    def __init__(self, graph, texts, fake, model):
        self.g, self.texts, self.fake = graph, texts, fake
        self.path = os.path.join(CACHE_DIR, "fake-judgments.json" if fake else "judgments.json")
        self.cache = json.load(open(self.path, encoding="utf-8")) if os.path.exists(self.path) else {}
        self.lock = threading.Lock()
        self.model_used = "fake word-overlap stand-in" if fake else None
        self.calls = self.tokens = 0
        if not fake:
            from typesafe_sdk import RetryPolicy, Score, TypeSafeClient
            self.client = TypeSafeClient(model=model, retry=RetryPolicy(max_retries=6, backoff_max=20.0))
            self.question = {"related": Score(instructions=QUESTION, criteria=LEVELS)}

    def card(self, i, n):
        return {"case": self.g.names[i], "year": self.g.years[i], "syllabus": clip(self.texts.summary(i), n)}

    def score(self, target, cand):
        key = f"{self.g.ids[target]}:{self.g.ids[cand]}"
        with self.lock:
            if key in self.cache:
                return self.cache[key]
        if self.fake:
            words = lambda i: set(re.findall(r"[a-z]{5,}", (self.g.names[i] + " " + self.texts.summary(i)).lower()))
            a, b = words(target), words(cand)
            s = round(4 * len(a & b) / (len(a | b) or 1), 4)
        else:
            r = self.client.system_one(state=[self.card(target, 1500), self.card(cand, 700)], questions=self.question)
            s = round(float(r.answers["related"].score), 4)
            with self.lock:
                self.model_used = r.model
                self.calls += 1
                self.tokens += getattr(r.usage, "input_tokens", 0) or 0
        with self.lock:
            self.cache[key] = s
        return s

    def save(self):
        with self.lock:
            os.makedirs(CACHE_DIR, exist_ok=True)
            json.dump(self.cache, open(self.path, "w", encoding="utf-8"))


# ----------------------------------------------------------------------------- race
def candidates(g, at, visited, mode, cap):
    """What a player could click from here, trimmed to the `cap` most-cited when a list is huge."""
    c = [x for x in g.neighbours(at, mode) if x not in visited]
    if len(c) > cap:
        c = sorted(c, key=lambda x: (-g.cited_all[x], x))[:cap]
    return c


def race(g, judge, pool, start, target, mode, max_hops, cap):
    """Jev's route. At a dead end it steps back, as a player can, and tries its next-warmest case."""
    path, scores, visited = [start], [], {start}
    for _ in range(max_hops * 3):  # moves made, dead ends included
        if path[-1] == target or len(path) - 1 >= max_hops:
            break
        cands = candidates(g, path[-1], visited, mode, cap)
        if not cands:
            if len(path) == 1:
                break
            path.pop()
            scores.pop()
            continue
        if target in cands:
            move, s = target, None
        else:
            got = list(pool.map(lambda c: judge.score(target, c), cands))
            best = max(range(len(cands)), key=lambda k: (got[k], g.cited_all[cands[k]], -cands[k]))
            move, s = cands[best], got[best]
        path.append(move)
        scores.append(s)
        visited.add(move)
    return {"path": [g.ids[x] for x in path], "score": scores, "reached": path[-1] == target}


def notable_targets(g, min_views):
    """Graph indexes of cases whose Wikipedia article is read at least min_views times a year (scripts/notoriety.py)."""
    path = os.path.join(DOCS_DATA, "notable.json")
    if not os.path.exists(path):
        return None
    cases = json.load(open(path, encoding="utf-8"))["cases"]
    return [g.by_cl[cl] for cl, views, _ in cases if views >= min_views and cl in g.by_cl and g.real[g.by_cl[cl]]]


def random_pool(g, mode, size, seed, targets=None, hops=(2, 3)):
    """Pairs for the random row: a notable target (any real opinion when no notable list exists) and a start
    `hops` away under the mode. The reverse search from the target finds starts in the mode's direction."""
    rng = random.Random(f"jev-pool:{seed}:{mode}")
    eligible = [i for i in range(g.n) if g.real[i]]
    reverse = {"any": "any", "back": "forward", "forward": "back"}[mode]
    out, seen = [], set()
    for _ in range(size * 50):
        if len(out) >= size:
            break
        target = rng.choice(targets or eligible)
        dist = g.bfs(target, reverse, hops[1])
        cands = sorted(s for s, d in dist.items() if hops[0] <= d <= hops[1] and g.real[s])
        if not cands:
            continue
        start = rng.choice(cands)
        if (start, target) not in seen:
            seen.add((start, target))
            out.append((start, target))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modes", default=",".join(MODES), help="comma-separated: any,back,forward")
    ap.add_argument("--pool", type=int, default=20, help="random pairs per mode (default 20)")
    ap.add_argument("--min-views", type=int, default=5000, help="random targets: Wikipedia views per year at least this (default 5000)")
    ap.add_argument("--hops", default="2-3", help="random pairs: shortest path range under the mode (default 2-3)")
    ap.add_argument("--max-hops", type=int, default=12, help="Jev gives up after this many hops (default 12)")
    ap.add_argument("--cap", type=int, default=150, help="most candidates judged per hop (default 150)")
    ap.add_argument("--workers", type=int, default=6, help="concurrent Jev calls (TypeSafe 429s past about 8)")
    ap.add_argument("--model", default="jev-1.13.0", help="Jev model (default jev-1.13.0, the first run's; pinned so reruns replay the same Jev)")
    ap.add_argument("--no-fetch", action="store_true", help="never fetch text from static.case.law")
    ap.add_argument("--fake", action="store_true", help="word-overlap stand-in instead of Jev; writes to --out only")
    ap.add_argument("--out", default=os.path.join(DOCS_DATA, "jev.json"))
    args = ap.parse_args()
    load_dotenv()
    if not args.fake and not os.environ.get("TYPESAFE_API_KEY"):
        raise SystemExit("TYPESAFE_API_KEY is not set: put it in .env or the environment, or pass --fake")
    modes = [m for m in args.modes.split(",") if m]
    if any(m not in MODES for m in modes):
        raise SystemExit(f"--modes must be from {MODES}")

    g = Graph(os.path.join(DOCS_DATA, "graph.json"))
    starters = json.load(open(os.path.join(DOCS_DATA, "starters.json"), encoding="utf-8"))
    texts = Texts(g, fetch=not args.no_fetch)
    judge = Judge(g, texts, args.fake, args.model)

    # Keep routes from earlier runs for modes not rerun now.
    prev = json.load(open(args.out, encoding="utf-8")) if os.path.exists(args.out) else {}
    routes = {k: v for k, v in prev.get("routes", {}).items() if k.split(":")[0] not in modes}
    pool_out = {m: v for m, v in prev.get("pool", {}).items() if m not in modes}

    targets = notable_targets(g, args.min_views)
    hops = tuple(int(x) for x in args.hops.split("-"))
    log(f"random targets: {len(targets) if targets else 'any real opinion (no notable.json)'}, {hops[0]} to {hops[1]} hops")
    jobs = []
    for mode in modes:
        for s in starters:
            if s["shortest"].get(mode) is None:
                continue
            older, newer = s["older"]["id"], s["newer"]["id"]  # graph indexes, as in app/static-api.js
            jobs.append((mode, *((newer, older) if mode == "back" else (older, newer))))
        pairs = random_pool(g, mode, args.pool, 1, targets, hops)
        pool_out[mode] = [f"{g.ids[a]}-{g.ids[b]}" for a, b in pairs]
        jobs += [(mode, a, b) for a, b in pairs]

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for k, (mode, a, b) in enumerate(jobs, 1):
            r = race(g, judge, pool, a, b, mode, args.max_hops, args.cap)
            routes[f"{mode}:{g.ids[a]}-{g.ids[b]}"] = r
            log(f"[{k}/{len(jobs)}] {mode}: {g.names[a]} -> {g.names[b]}: "
                f"{'reached in ' + str(len(r['path']) - 1) if r['reached'] else 'gave up after ' + str(len(r['path']) - 1)}"
                f"  ({time.time() - t0:.0f}s, {judge.calls} calls)")
            if k % 5 == 0:
                judge.save()
                texts.save()
    judge.save()
    texts.save()

    out = {"model": judge.model_used, "built": time.strftime("%Y-%m-%d %H:%M:%S"), "max_hops": args.max_hops,
           "pool": pool_out, "routes": routes}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
    done = sum(r["reached"] for r in routes.values())
    log(f"wrote {args.out}: {len(routes)} routes, {done} reached; {judge.calls} Jev calls, "
        f"{judge.tokens:,} input tokens (about ${judge.tokens * 0.042 / 1e6:.2f})")


if __name__ == "__main__":
    main()

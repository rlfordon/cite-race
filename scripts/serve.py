"""Citation-race prototype server (stdlib only).

    python -I scripts/serve.py [--port 8765] [--rebuild]

Serves app/index.html at / (and any file under app/ by path) and the JSON API described in
notes/prototype-api.md. Data: the CourtListener merged SCOTUS graph restricted to its giant
component (boilerplate hubs from scripts/exclusions.py removed first) and CAP opinion HTML read
lazily from data/cap/raw/*/<vol>.zip. The index is cached in data/prototype/index.pickle on the
first run (see scripts/prototype_index.py).

The raw zips are untrusted downloads: members are only ever decoded as text / json.loads()'d.
"""
import argparse
import functools
import json
import mimetypes
import os
import random
import sys
import time
import zipfile
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # our own scripts dir
import cap_text  # noqa: E402
import prototype_index  # noqa: E402

ROOT = prototype_index.ROOT
APP_DIR = os.path.join(ROOT, "app")
MODES = ("any", "back", "forward")
NODE_KEYS = ("id", "name", "cite", "year", "date", "cited_all", "cited_scotus", "has_text")

INDEX = None
NODES = OUT_ADJ = IN_ADJ = UND_ADJ = TEXT = CAP_TO_CL = None
ELIGIBLE = None  # sorted ids usable as puzzle endpoints


# ----------------------------------------------------------------------------- graph helpers
def node_obj(cid):
    n = NODES[cid]
    return {k: n[k] for k in NODE_KEYS}


def neighbours(cid, mode):
    """Nodes reachable in one hop from cid under the mode."""
    if mode == "back":
        return OUT_ADJ.get(cid, ())
    if mode == "forward":
        return IN_ADJ.get(cid, ())
    return UND_ADJ.get(cid, ())


def reverse_neighbours(cid, mode):
    """Nodes that can reach cid in one hop under the mode."""
    if mode == "back":
        return IN_ADJ.get(cid, ())
    if mode == "forward":
        return OUT_ADJ.get(cid, ())
    return neighbours(cid, "any")


def bfs_from(start, mode, max_depth=None):
    """dist dict from start following allowed hops."""
    dist = {start: 0}
    q = deque([start])
    while q:
        x = q.popleft()
        d = dist[x]
        if max_depth is not None and d >= max_depth:
            continue
        for y in neighbours(x, mode):
            if y not in dist:
                dist[y] = d + 1
                q.append(y)
    return dist


@functools.lru_cache(maxsize=128)
def dist_to_target(target, mode):
    """dist[x] = hops from x to target under the mode (BFS backwards from the target)."""
    dist = {target: 0}
    q = deque([target])
    while q:
        x = q.popleft()
        d = dist[x]
        for y in reverse_neighbours(x, mode):
            if y not in dist:
                dist[y] = d + 1
                q.append(y)
    return dist


def shortest_path(a, b, mode):
    if a == b:
        return [a]
    parent = {a: None}
    q = deque([a])
    while q:
        x = q.popleft()
        for y in neighbours(x, mode):
            if y in parent:
                continue
            parent[y] = x
            if y == b:
                path = [b]
                while parent[path[-1]] is not None:
                    path.append(parent[path[-1]])
                return path[::-1]
            q.append(y)
    return None


# ----------------------------------------------------------------------------- API
def par_for(shortest):
    """Shortest + 2, except a one-hop warm-up, whose par is the hop itself."""
    return 1 if shortest == 1 else shortest + 2


def api_puzzle(seed, mode):
    rng = random.Random(f"{seed}:{mode}" if mode != "any" else seed)
    for _ in range(500):
        start = rng.choice(ELIGIBLE)
        dist = bfs_from(start, mode, max_depth=5)
        cands = sorted(t for t, d in dist.items() if 3 <= d <= 5 and NODES[t]["real"])
        if not cands:
            continue
        target = rng.choice(cands)
        shortest = dist[target]
        return {"seed": seed, "mode": mode, "start": node_obj(start), "target": node_obj(target),
                "shortest": shortest, "par": par_for(shortest)}
    return None


STARTERS = None


def load_starters():
    global STARTERS
    path = os.path.join(ROOT, "data", "prototype", "starters.json")
    try:
        with open(path, encoding="utf-8") as f:
            STARTERS = json.load(f)
    except OSError:
        STARTERS = []


def api_starters(mode):
    """Curated puzzles with the start/target oriented for the mode; those with no path in the mode are omitted."""
    out = []
    for s in STARTERS:
        d = s["shortest"].get(mode)
        if d is None:
            continue
        older, newer = s["older"], s["newer"]
        start, target = (newer, older) if mode == "back" else (older, newer)
        out.append({"group": s["group"], "theme": s["theme"], "start": start, "target": target,
                    "shortest": d, "par": par_for(d), "mode": mode, "seed": 0, "pair": f"{start['id']}-{target['id']}"})
    return out


def api_pair_puzzle(pair, mode):
    try:
        a, b = (int(x) for x in pair.split("-"))
    except ValueError:
        raise ApiError(400, "pair must be <startid>-<targetid>") from None
    if a not in NODES or b not in NODES:
        raise ApiError(404, "pair ids are not in the game graph")
    path = shortest_path(a, b, mode)
    if path is None:
        raise ApiError(404, "no path between that pair in this mode")
    d = len(path) - 1
    return {"seed": 0, "mode": mode, "pair": pair, "start": node_obj(a), "target": node_obj(b), "shortest": d, "par": par_for(d)}


def api_path(a, b, mode):
    path = shortest_path(a, b, mode)
    if path is None:
        return {"length": None, "mode": mode}
    return {"length": len(path) - 1, "mode": mode, "path": [node_obj(c) for c in path]}


def api_opponent(seed, at, target, visited, mode):
    rng = random.Random(f"{seed}:{at}:{mode}")
    cands = sorted(c for c in neighbours(at, mode) if c not in visited and c != at)
    if not cands:
        return {"move": None, "note": "stand-in: no unvisited neighbour"}
    if target in cands:
        return {"move": node_obj(target), "note": "stand-in (target in reach)"}
    dist = dist_to_target(target, mode)
    here = dist.get(at)
    closer = [c for c in cands if here is not None and dist.get(c) == here - 1]
    roll = rng.random()
    if roll < 0.6 and closer:
        move, how = rng.choice(closer), "closer"
    else:
        top = sorted(cands, key=lambda c: (-NODES[c]["cited_all"], c))[:10]
        move, how = rng.choice(top), "random-top10"
    return {"move": node_obj(move), "note": f"stand-in ({how})"}


def read_zip_member(zip_rel, member):
    with zipfile.ZipFile(os.path.join(ROOT, zip_rel)) as z:
        return z.read(member)


def case_html(cid):
    """(html, stats) for a node with text; ('', {}) otherwise."""
    t = TEXT.get(cid)
    if t is None:
        return "", {}
    zip_rel, member, cap_id, _wc = t
    raw = read_zip_member(zip_rel, member).decode("utf-8", "replace")
    cites_to = []
    try:
        meta = json.loads(read_zip_member(zip_rel, member.replace("html/", "json/", 1)[:-5] + ".json").decode("utf-8"))
        cites_to = meta.get("cites_to") or []
    except Exception:  # noqa: BLE001  (missing/odd json: links still come from CAP's anchors)
        pass
    return cap_text.render(raw, cites_to, lambda cap: CAP_TO_CL.get(cap), self_id=cid)


def api_case(cid):
    html, stats = case_html(cid)
    cites = sorted(OUT_ADJ.get(cid, ()), key=lambda c: (NODES[c]["year"] or 0, NODES[c]["date"], c))
    cited_by = sorted(IN_ADJ.get(cid, ()), key=lambda c: (-NODES[c]["cited_all"], c))
    out = node_obj(cid)
    out.update({"html": html, "cites": [node_obj(c) for c in cites],
                "cited_by": [node_obj(c) for c in cited_by], "cited_by_total": len(cited_by),
                "text_stats": stats})
    if not html:
        out["note"] = "no CAP text for this case (post-2020 or unmatched)"
    return out


# ----------------------------------------------------------------------------- HTTP
class ApiError(Exception):
    def __init__(self, status, msg):
        super().__init__(msg)
        self.status = status


def q_int(qs, key, default=None):
    v = qs.get(key, [None])[0]
    if v is None or v == "":
        if default is None:
            raise ApiError(400, f"missing {key}")
        return default
    try:
        return int(v)
    except ValueError:
        raise ApiError(400, f"{key} must be an integer") from None


def q_mode(qs):
    m = qs.get("mode", ["any"])[0] or "any"
    if m not in MODES:
        raise ApiError(400, "mode must be any, back or forward")
    return m


def q_node(qs, key):
    cid = q_int(qs, key)
    if cid not in NODES:
        raise ApiError(404, f"{key}={cid} is not a node of the game graph")
    return cid


class Handler(BaseHTTPRequestHandler):
    server_version = "cite-race/0"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlsplit(self.path)
        path = unquote(u.path)
        qs = parse_qs(u.query)
        try:
            if path.startswith("/api/"):
                self.send_json(self.route_api(path, qs))
            else:
                self.serve_static(path)
        except ApiError as e:
            self.send_json({"error": str(e)}, e.status)
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            self.send_json({"error": f"{type(e).__name__}: {e}"}, 500)

    def route_api(self, path, qs):
        parts = path.strip("/").split("/")  # ['api', ...]
        if parts[1:] == ["starters"]:
            return api_starters(q_mode(qs))
        if parts[1:] == ["puzzle"]:
            seed = q_int(qs, "seed", 1)
            mode = q_mode(qs)
            pair = qs.get("pair", [""])[0]
            if pair:
                return api_pair_puzzle(pair, mode)
            res = api_puzzle(seed, mode)
            if res is None:
                raise ApiError(500, "could not find a puzzle for this seed")
            return res
        if parts[1:] == ["path"]:
            return api_path(q_node(qs, "from"), q_node(qs, "to"), q_mode(qs))
        if parts[1:] == ["opponent"]:
            visited = set()
            for v in qs.get("visited", [""])[0].split(","):
                v = v.strip()
                if v:
                    try:
                        visited.add(int(v))
                    except ValueError:
                        raise ApiError(400, "visited must be comma-separated ids") from None
            return api_opponent(q_int(qs, "puzzle", 0), q_node(qs, "at"), q_node(qs, "target"),
                                visited, q_mode(qs))
        if len(parts) == 3 and parts[1] == "case":
            try:
                cid = int(parts[2])
            except ValueError:
                raise ApiError(400, "case id must be an integer") from None
            if cid not in NODES:
                raise ApiError(404, f"{cid} is not a node of the game graph (unknown, isolated, or a boilerplate hub)")
            return api_case(cid)
        if parts[1:] == ["stats"]:
            return {"built": INDEX["built"], **INDEX["stats"], "eligible": len(ELIGIBLE)}
        raise ApiError(404, "unknown API route")

    def serve_static(self, path):
        if path in ("", "/"):
            path = "/index.html"
        rel = os.path.normpath(path.lstrip("/"))
        full = os.path.normpath(os.path.join(APP_DIR, rel))
        if not (full == APP_DIR or full.startswith(APP_DIR + os.sep)) or not os.path.isfile(full):
            if rel == "index.html":
                raise ApiError(503, "app/index.html is not there yet")
            raise ApiError(404, "not found")
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        with open(full, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def load(force=False):
    global INDEX, NODES, OUT_ADJ, IN_ADJ, UND_ADJ, TEXT, CAP_TO_CL, ELIGIBLE
    INDEX = prototype_index.load(force=force)
    NODES, OUT_ADJ, IN_ADJ = INDEX["nodes"], INDEX["out_adj"], INDEX["in_adj"]
    UND_ADJ = {}
    for cid in NODES:
        UND_ADJ[cid] = sorted(set(OUT_ADJ.get(cid, ())) | set(IN_ADJ.get(cid, ())))
    TEXT, CAP_TO_CL = INDEX["text"], INDEX["cap_to_cl"]
    ELIGIBLE = sorted(cid for cid, n in NODES.items() if n["real"])
    load_starters()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--rebuild", action="store_true", help="rebuild data/prototype/index.pickle")
    args = ap.parse_args()
    t = time.time()
    load(force=args.rebuild)
    print(f"ready in {time.time() - t:.1f}s: {len(NODES)} nodes, {INDEX['stats']['edges']} edges, "
          f"{len(TEXT)} with text, {len(ELIGIBLE)} puzzle-eligible", file=sys.stderr)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.daemon_threads = True
    print(f"serving http://{args.host}:{args.port}/  (Ctrl-C to stop)", file=sys.stderr)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()

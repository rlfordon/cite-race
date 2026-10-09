"""Build / load the cached index used by scripts/serve.py.

Inputs (all project-local, read-only):
  data/courtlistener/scotus_nodes_merged.csv, scotus_edges_merged.csv   (the game graph)
  data/cap/scotus_nodes.csv, scotus_alias_sct_to_us.csv                 (CAP metadata)
  data/cap/raw/us/<vol>.zip, data/cap/raw/s-ct/<vol>.zip                (metadata/CasesMetadata.json
                                                                          gives html member names)
Outputs (data/prototype/):
  index.pickle           everything serve.py needs, loads in ~1 s
  cap_text_index.csv     cl_id, cap_id, zip_path, member_path, word_count, cap_name (human-readable
                         copy of the text index)

Run directly to (re)build:  python -I scripts/prototype_index.py [--force]
The raw zips are untrusted downloads: only json.loads() is ever applied to their members.
"""
import csv
import glob
import json
import os
import pickle
import re
import sys
import time
import zipfile
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # our own scripts dir
from exclusions import EXCLUDED_IDS, verify as verify_exclusions  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CL_DIR = os.path.join(ROOT, "data", "courtlistener")
CAP_DIR = os.path.join(ROOT, "data", "cap")
OUT_DIR = os.path.join(ROOT, "data", "prototype")
PICKLE = os.path.join(OUT_DIR, "index.pickle")
TEXT_CSV = os.path.join(OUT_DIR, "cap_text_index.csv")
INDEX_VERSION = 5
REAL_MIN_WORDS = 300

csv.field_size_limit(1 << 30)

STOP = {"v", "vs", "the", "of", "co", "inc", "et", "al", "and", "corp", "company", "a", "an",
        "in", "re", "ex", "parte", "rel", "ltd", "llc", "no", "on", "by", "for", "to", "at",
        "mr", "mrs", "his", "her", "their", "its"}


def name_tokens(name):
    return set(re.findall(r"[a-z0-9]+", (name or "").lower())) - STOP


def name_overlap(a, b):
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


GENERIC = {"united", "states", "state", "city", "county", "people", "commonwealth", "board", "bank",
           "railroad", "railway", "company", "commissioner", "director", "secretary", "attorney", "general"}


def name_jaccard(a, b):
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def same_case(meta_a, meta_b):
    """Strict rule for folding two clusters: same year and (same U.S. cite or Jaccard >= 0.6)."""
    if not meta_a["year"] or meta_a["year"] != meta_b["year"]:
        return False
    if meta_a["us_cite"] and meta_a["us_cite"] == meta_b["us_cite"]:
        return True
    return name_jaccard(meta_a["name"], meta_b["name"]) >= 0.6


def related_case(meta_a, meta_b):
    """Looser rule for dropping an edge: same year, names share >= half their non-generic tokens."""
    if not meta_a["year"] or meta_a["year"] != meta_b["year"]:
        return False
    ta = name_tokens(meta_a["name"]) - GENERIC
    tb = name_tokens(meta_b["name"]) - GENERIC
    if not ta or not tb:
        return False
    return len(ta & tb) / min(len(ta), len(tb)) >= 0.5


def log(msg):
    print(f"[index] {msg}", file=sys.stderr, flush=True)


# ----------------------------------------------------------------------------- CourtListener
def load_meta():
    """cluster_id -> {year, name, us_cite} for every CL node (light pass over the nodes file)."""
    meta = {}
    with open(os.path.join(CL_DIR, "scotus_nodes_merged.csv"), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            meta[int(row["cluster_id"])] = {"year": int(row["year"]) if row["year"] else None,
                                            "name": row["case_name"], "us_cite": row["us_cite"]}
    return meta


def fold_duplicates(edges, meta):
    """CL still holds some cases twice (slip opinion + bound volume, or two imports with different
    dates) and one copy cites the other. Fold a->b when the two look like the same case
    (same_case) into the better-connected one. Returns (edges, folded: dup_id -> canonical)."""
    deg = defaultdict(int)
    for a, b in edges:
        deg[a] += 1
        deg[b] += 1
    parent = {}

    def find(x):
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x

    for a, b in edges:
        if a in meta and b in meta and same_case(meta[a], meta[b]):
            ra, rb = find(a), find(b)
            if ra == rb:
                continue
            keep, drop = (ra, rb) if (deg[ra], -ra) >= (deg[rb], -rb) else (rb, ra)
            parent[drop] = keep
    folded = {x: find(x) for x in parent if find(x) != x}
    new_edges = set()
    self_loops = 0
    for a, b in edges:
        a2, b2 = folded.get(a, a), folded.get(b, b)
        if a2 == b2:
            self_loops += 1
            continue
        new_edges.add((a2, b2))
    log(f"folded {len(folded)} duplicate clusters into {len(set(folded.values()))} canonical ones; "
        f"dropped {self_loops} self-edges")
    return sorted(new_edges), folded


def load_graph():
    """Edges minus excluded hubs, minus edges that point forward in time (a citing opinion cannot
    cite a later case; ~270 such edges are CL resolution noise), with duplicate clusters folded and
    same-year same-name edges dropped, restricted to the giant undirected component.
    Returns (giant, out_adj, in_adj, folded)."""
    meta = load_meta()
    edges = []
    dropped_time = 0
    with open(os.path.join(CL_DIR, "scotus_edges_merged.csv"), newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            a, b = int(row[0]), int(row[1])
            if a in EXCLUDED_IDS or b in EXCLUDED_IDS or a == b:
                continue
            ya, yb = meta.get(a, {}).get("year"), meta.get(b, {}).get("year")
            if ya and yb and yb > ya:
                dropped_time += 1
                continue
            edges.append((a, b))
    log(f"dropped {dropped_time} edges that point forward in time")
    edges, folded = fold_duplicates(edges, meta)
    out_adj, in_adj = defaultdict(set), defaultdict(set)
    dropped_related = 0
    for a, b in edges:
        if a in meta and b in meta and related_case(meta[a], meta[b]):
            dropped_related += 1
            continue
        out_adj[a].add(b)
        in_adj[b].add(a)
    log(f"dropped {dropped_related} remaining same-year edges between related names")
    und = defaultdict(set)
    for a, bs in out_adj.items():
        for b in bs:
            und[a].add(b)
            und[b].add(a)
    seen, giant = set(), set()
    for s in und:
        if s in seen:
            continue
        comp, stack = {s}, [s]
        seen.add(s)
        while stack:
            x = stack.pop()
            for y in und[x]:
                if y not in seen:
                    seen.add(y)
                    comp.add(y)
                    stack.append(y)
        if len(comp) > len(giant):
            giant = comp
    out_adj = {a: sorted(b for b in bs if b in giant) for a, bs in out_adj.items() if a in giant}
    in_adj = {a: sorted(b for b in bs if b in giant) for a, bs in in_adj.items() if a in giant}
    log(f"edges loaded; active {len(und)}, giant component {len(giant)}")
    folded = {d: c for d, c in folded.items() if c in giant}
    return giant, out_adj, in_adj, folded


def load_cl_nodes(giant, folded):
    """Node rows for the giant component. Folded duplicates contribute their cites (so CAP links to
    the duplicate's cite still resolve) and their in-degree counts to the canonical node."""
    nodes = {}
    dups = {}
    with open(os.path.join(CL_DIR, "scotus_nodes_merged.csv"), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cid = int(row["cluster_id"])
            if cid in folded:
                dups[cid] = row
                continue
            if cid not in giant:
                continue
            nodes[cid] = {
                "id": cid,
                "name": row["case_name"],
                "cite": row["us_cite"] or (row["all_cites"].split(" | ")[0] if row["all_cites"] else ""),
                "us_cite": row["us_cite"],
                "all_cites": [c.strip() for c in row["all_cites"].split("|") if c.strip()],
                "year": int(row["year"]) if row["year"] else None,
                "date": row["date_filed"],
                "cited_all": int(row["indeg_all_courts"] or 0),
                "cited_scotus": int(row["indeg_scotus"] or 0),
            }
    for dup, canon in folded.items():
        row = dups.get(dup)
        n = nodes.get(canon)
        if row is None or n is None:
            continue
        extra = [c.strip() for c in row["all_cites"].split("|") if c.strip()]
        if row["us_cite"]:
            extra.append(row["us_cite"])
        n["all_cites"] += [c for c in extra if c not in n["all_cites"]]
        n["cited_all"] += int(row["indeg_all_courts"] or 0)
        n["cited_scotus"] += int(row["indeg_scotus"] or 0)
    log(f"CL nodes in giant component: {len(nodes)} (+{len(folded)} folded duplicates)")
    return nodes


# ----------------------------------------------------------------------------- CAP
def load_cap_nodes():
    caps = {}
    with open(os.path.join(CAP_DIR, "scotus_nodes.csv"), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cid = int(row["cap_case_id"])
            caps[cid] = {
                "id": cid,
                "name": row["case_name"],
                "us_cite": row["us_cite"],
                "sct_cite": row["sct_cite"],
                "led_cite": row["led_cite"],
                "year": int(row["year"]) if row["year"] else None,
                "reporter": row["source_reporter"],
                "volume": row["source_volume"],
                "word_count": int(row["word_count"] or 0),
            }
    alias = {}
    with open(os.path.join(CAP_DIR, "scotus_alias_sct_to_us.csv"), newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            alias[int(row[0])] = int(row[1])
    log(f"CAP nodes: {len(caps)}, S. Ct. aliases: {len(alias)}")
    return caps, alias


def scan_zip_members():
    """cap_id -> (zip path relative to ROOT, html member path). Reads CasesMetadata.json only."""
    members = {}
    files = []
    for rep in ("us", "s-ct"):
        files += sorted(glob.glob(os.path.join(CAP_DIR, "raw", rep, "*.zip")),
                        key=lambda p: int(os.path.basename(p).split(".")[0]))
    t = time.time()
    for i, path in enumerate(files):
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        try:
            with zipfile.ZipFile(path) as z:
                names = set(z.namelist())
                data = json.loads(z.read("metadata/CasesMetadata.json").decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            log(f"WARN cannot read {path}: {e}")
            continue
        for c in data:
            try:
                cid = int(c["id"])
                fn = str(c["file_name"])
            except (KeyError, TypeError, ValueError):
                continue
            member = f"html/{fn}.html"
            if member in names:
                members[cid] = (rel, member)
        if (i + 1) % 100 == 0:
            log(f"  scanned {i + 1}/{len(files)} zips ({time.time() - t:.0f}s)")
    log(f"zip members: {len(members)} cases in {len(files)} zips ({time.time() - t:.0f}s)")
    return members


# ----------------------------------------------------------------------------- joins
def build_maps(nodes, out_adj, in_adj, caps, alias):
    degree = {cid: len(out_adj.get(cid, ())) + len(in_adj.get(cid, ())) for cid in nodes}

    cl_by_cite = defaultdict(list)  # any cite string -> cl ids
    for cid, n in nodes.items():
        for c in n["all_cites"]:
            cl_by_cite[c].append(cid)
        if n["us_cite"] and n["us_cite"] not in n["all_cites"]:
            cl_by_cite[n["us_cite"]].append(cid)

    # CAP id -> CL id (for resolving cites_to in the text)
    cap_to_cl = {}
    for cap in caps.values():
        cands = []
        if cap["us_cite"]:
            cands = cl_by_cite.get(cap["us_cite"], [])
        if not cands:
            for c in (cap["sct_cite"], cap["led_cite"]):
                if c:
                    cands = cl_by_cite.get(c, [])
                    if cands:
                        break
        if not cands:
            continue
        if len(cands) == 1:
            cap_to_cl[cap["id"]] = cands[0]
            continue

        def key(cid, cap=cap):
            n = nodes[cid]
            return (name_overlap(cap["name"], n["name"]) >= 0.5, degree[cid],
                    n["year"] == cap["year"])
        cap_to_cl[cap["id"]] = max(cands, key=key)
    for sct_id, us_id in alias.items():
        if us_id in cap_to_cl and sct_id not in cap_to_cl:
            cap_to_cl[sct_id] = cap_to_cl[us_id]
    log(f"CAP->CL resolved: {len(cap_to_cl)} of {len(caps)} CAP records")

    # CL id -> CAP record (for the text)
    cap_by_cite = defaultdict(list)
    for cap in caps.values():
        for c in (cap["us_cite"], cap["sct_cite"], cap["led_cite"]):
            if c:
                cap_by_cite[c].append(cap["id"])
    cl_to_cap = {}
    for cid, n in nodes.items():
        cands = cap_by_cite.get(n["us_cite"], []) if n["us_cite"] else []
        if not cands:
            for c in n["all_cites"]:
                if " S. Ct. " in c or " L. Ed. " in c:
                    cands = cap_by_cite.get(c, [])
                    if cands:
                        break
        cands = sorted(set(cands))
        if not cands:
            continue
        if len(cands) == 1:
            cl_to_cap[cid] = cands[0]
            continue
        scored = sorted(cands, key=lambda k: (name_overlap(n["name"], caps[k]["name"]),
                                              caps[k]["year"] == n["year"],
                                              caps[k]["word_count"]), reverse=True)
        best = scored[0]
        if name_overlap(n["name"], caps[best]["name"]) >= 0.5:
            cl_to_cap[cid] = best
        else:
            # several CAP records on the page and none shares the name: only accept the
            # single real opinion among them if the CL node itself looks like a real case
            reals = [k for k in cands if caps[k]["word_count"] >= REAL_MIN_WORDS]
            if len(reals) == 1 and caps[reals[0]]["year"] == n["year"]:
                cl_to_cap[cid] = reals[0]
    log(f"CL->CAP text matches: {len(cl_to_cap)} of {len(nodes)} nodes")
    return cap_to_cl, cl_to_cap


def build(force=False):
    t0 = time.time()
    os.makedirs(OUT_DIR, exist_ok=True)
    giant, out_adj, in_adj, folded = load_graph()
    nodes = load_cl_nodes(giant, folded)
    problems = verify_exclusions({cid: {"us_cite": n["us_cite"]} for cid, n in nodes.items()})
    # excluded ids are removed from the graph, so "not in node table" is expected here
    problems = [p for p in problems if "not in node table" not in p]
    if problems:
        log("WARN exclusions: " + "; ".join(problems))
    caps, alias = load_cap_nodes()
    members = scan_zip_members()
    cap_to_cl, cl_to_cap = build_maps(nodes, out_adj, in_adj, caps, alias)

    text = {}
    for cid, cap_id in cl_to_cap.items():
        m = members.get(cap_id)
        if m is None:
            continue
        text[cid] = (m[0], m[1], cap_id, caps[cap_id]["word_count"])
    for cid, n in nodes.items():
        n["has_text"] = cid in text
        n["real"] = cid in text and text[cid][3] >= REAL_MIN_WORDS
        del n["all_cites"]
        del n["us_cite"]

    with open(TEXT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cl_id", "cap_id", "zip_path", "member_path", "word_count", "cap_name"])
        for cid in sorted(text):
            z, m, cap_id, wc = text[cid]
            w.writerow([cid, cap_id, z, m, wc, caps[cap_id]["name"]])

    index = {
        "version": INDEX_VERSION,
        "built": time.strftime("%Y-%m-%d %H:%M:%S"),
        "nodes": nodes,
        "out_adj": out_adj,
        "in_adj": in_adj,
        "text": text,
        "cap_to_cl": cap_to_cl,
        "folded": folded,
        "stats": {
            "nodes": len(nodes), "edges": sum(len(v) for v in out_adj.values()), "folded": len(folded),
            "with_text": len(text), "real": sum(1 for n in nodes.values() if n["real"]),
            "cap_to_cl": len(cap_to_cl), "build_seconds": round(time.time() - t0, 1),
        },
    }
    with open(PICKLE + ".tmp", "wb") as f:
        pickle.dump(index, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(PICKLE + ".tmp", PICKLE)
    log(f"built in {time.time() - t0:.1f}s: {index['stats']}")
    return index


def load(force=False):
    if not force and os.path.exists(PICKLE):
        t = time.time()
        with open(PICKLE, "rb") as f:
            index = pickle.load(f)
        if index.get("version") == INDEX_VERSION:
            log(f"loaded {PICKLE} in {time.time() - t:.1f}s: {index['stats']}")
            return index
        log("cached index is from an older version; rebuilding")
    return build(force=True)


if __name__ == "__main__":
    load(force="--force" in sys.argv or not os.path.exists(PICKLE))

"""Build the GitHub Pages site in docs/ from the prototype index.

    python -I scripts/build_static.py

Writes:
  docs/data/graph.json      the game graph, nodes re-indexed 0..N-1 (sorted by CL cluster id)
  docs/data/starters.json   data/prototype/starters.json with node ids re-indexed (CL id kept as cl_id)
  docs/index.html           app/index.html with <body data-static="1">
  docs/static-api.js        copy of app/static-api.js
  docs/.nojekyll

graph.json shape (all arrays indexed by the new node index):
  ids, names, cites, years, dates, cited_all, cited_scotus, has_text, real,
  text     null or [reporter, vol, member]; the archive URL is
           https://static.case.law/<reporter>/<vol>/html/<member>.html
  cap_ids  list of CAP case ids that resolve to the node (for linkifying CAP's citation anchors)
  edges    flat [citing, cited, citing, cited, ...] in new indexes, sorted by (citing, cited)
"""
import gzip
import json
import os
import re
import shutil
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # our own scripts dir
import prototype_index  # noqa: E402

ROOT = prototype_index.ROOT
DOCS = os.path.join(ROOT, "docs")
NODE_KEYS = ("id", "name", "cite", "year", "date", "cited_all", "cited_scotus", "has_text")


def log(msg):
    print(f"[static] {msg}", file=sys.stderr, flush=True)


def text_triple(t):
    """('data/cap/raw/us/304.zip', 'html/0064-01.html', cap_id, wc) -> ['us', 304, '0064-01']"""
    zip_rel, member = t[0], t[1]
    m = re.fullmatch(r"data/cap/raw/(us|s-ct)/(\d+)\.zip", zip_rel.replace("\\", "/"))
    if not m:
        raise ValueError(f"unexpected zip path {zip_rel}")
    mm = re.fullmatch(r"html/([^/]+)\.html", member)
    if not mm:
        raise ValueError(f"unexpected member path {member}")
    return [m.group(1), int(m.group(2)), mm.group(1)]


def build_graph(index):
    nodes, out_adj = index["nodes"], index["out_adj"]
    order = sorted(nodes)  # fixed order: ascending CL cluster id
    pos = {cid: i for i, cid in enumerate(order)}
    caps = defaultdict(list)
    for cap_id, cl in index["cap_to_cl"].items():
        if cl in pos:
            caps[cl].append(cap_id)
    g = {"ids": [], "names": [], "cites": [], "years": [], "dates": [], "cited_all": [], "cited_scotus": [],
         "has_text": [], "real": [], "text": [], "cap_ids": [], "edges": []}
    for cid in order:
        n = nodes[cid]
        g["ids"].append(cid)
        g["names"].append(n["name"])
        g["cites"].append(n["cite"] or "")
        g["years"].append(n["year"])
        g["dates"].append(n["date"] or "")
        g["cited_all"].append(n["cited_all"])
        g["cited_scotus"].append(n["cited_scotus"])
        g["has_text"].append(1 if n["has_text"] else 0)
        g["real"].append(1 if n["real"] else 0)
        t = index["text"].get(cid)
        g["text"].append(text_triple(t) if t else None)
        g["cap_ids"].append(sorted(caps.get(cid, ())))
    edges = g["edges"]
    for cid in order:
        a = pos[cid]
        for b_cl in sorted(out_adj.get(cid, ())):
            if b_cl in pos:
                edges.append(a)
                edges.append(pos[b_cl])
    g["meta"] = {"built": time.strftime("%Y-%m-%d %H:%M:%S"), "nodes": len(order), "edges": len(edges) // 2,
                 "with_text": sum(g["has_text"]), "real": sum(g["real"]), "index_built": index.get("built"),
                 "archive": "https://static.case.law/<reporter>/<vol>/html/<member>.html"}
    return g, pos


def build_starters(pos):
    src = os.path.join(ROOT, "data", "prototype", "starters.json")
    with open(src, encoding="utf-8") as f:
        starters = json.load(f)
    out = []
    for s in starters:
        s = dict(s)
        for key in ("older", "newer"):
            n = dict(s[key])
            cl = n["id"]
            if cl not in pos:
                raise ValueError(f"starter {n['name']} ({cl}) is not in the graph")
            n["cl_id"] = cl
            n["id"] = pos[cl]
            s[key] = n
        out.append(s)
    return out


def write_json(path, obj, compact=True):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        if compact:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(obj, f, ensure_ascii=False, indent=1)
    raw = os.path.getsize(path)
    with open(path, "rb") as f:
        gz = len(gzip.compress(f.read(), compresslevel=9))
    log(f"{os.path.relpath(path, ROOT)}: {raw / 1e6:.2f} MB raw, {gz / 1e6:.2f} MB gzipped")
    return raw, gz


def main():
    t0 = time.time()
    index = prototype_index.load()
    os.makedirs(os.path.join(DOCS, "data"), exist_ok=True)
    g, pos = build_graph(index)
    write_json(os.path.join(DOCS, "data", "graph.json"), g)
    write_json(os.path.join(DOCS, "data", "starters.json"), build_starters(pos), compact=False)

    with open(os.path.join(ROOT, "app", "index.html"), "rb") as f:  # bytes, so line endings survive
        page = f.read()
    if b"<body>" not in page:
        raise SystemExit("app/index.html has no plain <body> tag to mark")
    page = page.replace(b"<body>", b'<body data-static="1">', 1)
    with open(os.path.join(DOCS, "index.html"), "wb") as f:
        f.write(page)
    shutil.copyfile(os.path.join(ROOT, "app", "static-api.js"), os.path.join(DOCS, "static-api.js"))
    with open(os.path.join(DOCS, ".nojekyll"), "w") as f:
        f.write("")
    log(f"docs/ written in {time.time() - t0:.1f}s: {g['meta']}")


if __name__ == "__main__":
    main()

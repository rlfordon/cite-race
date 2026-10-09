#!/usr/bin/env python
"""Graph statistics for the CAP-derived SCOTUS citation graph.

Usage:
  python -I scripts/cap_graph_stats.py --data data/cap [--pairs 2000] [--seed 1] [--us-only]

Reads scotus_nodes.csv / scotus_edges.csv, prints markdown tables and writes them to
data/cap/graph_stats.md. Shortest paths are computed on the undirected graph with
scipy.sparse.csgraph (BFS from sampled sources), which is far faster than networkx BFS.
"""
import argparse, csv, os, random, sys
from collections import Counter

import networkx as nx
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, shortest_path

SANITY = [
    ("Bell Atlantic v. Twombly", "550 U.S. 544"),
    ("Ashcroft v. Iqbal", "556 U.S. 662"),
    ("Celotex v. Catrett", "477 U.S. 317"),
    ("Anderson v. Liberty Lobby", "477 U.S. 242"),
    ("Chevron v. NRDC", "467 U.S. 837"),
    ("Erie R. Co. v. Tompkins", "304 U.S. 64"),
    ("Marbury v. Madison", "5 U.S. 137"),
    ("Brown v. Board of Education", "347 U.S. 483"),
    ("Obergefell v. Hodges", "576 U.S. 644"),
    ("Bostock v. Clayton County", "140 S. Ct. 1731"),
]

out_lines = []


def emit(s=""):
    print(s)
    out_lines.append(s)


def table(headers, rows):
    emit("| " + " | ".join(headers) + " |")
    emit("|" + "|".join("---" for _ in headers) + "|")
    for r in rows:
        emit("| " + " | ".join(str(x) for x in r) + " |")
    emit()


def degree_hist(values, bins):
    c = Counter()
    for v in values:
        for lo, hi, label in bins:
            if lo <= v <= hi:
                c[label] += 1
                break
    n = len(values)
    return [(label, c[label], f"{100 * c[label] / n:.1f}%") for lo, hi, label in bins]


DEG_BINS = [(0, 0, "0"), (1, 1, "1"), (2, 5, "2-5"), (6, 10, "6-10"), (11, 25, "11-25"),
            (26, 50, "26-50"), (51, 100, "51-100"), (101, 250, "101-250"), (251, 500, "251-500"),
            (501, 1000, "501-1000"), (1001, 10 ** 9, ">1000")]


def path_distribution(G_und, pairs_n, rng, label):
    """Sample pairs within the largest connected component; BFS from sampled sources."""
    nodes = list(G_und.nodes())
    idx = {n: i for i, n in enumerate(nodes)}
    rows, cols = [], []
    for a, b in G_und.edges():
        rows.append(idx[a]); cols.append(idx[b])
    n = len(nodes)
    A = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n)).tocsr()
    ncomp, labels = connected_components(A, directed=False)
    big = Counter(labels).most_common(1)[0][0]
    lcc = np.where(labels == big)[0]
    emit(f"**{label}**: {n:,} nodes, {G_und.number_of_edges():,} undirected edges, "
         f"{ncomp:,} components; largest component {len(lcc):,} nodes "
         f"({100 * len(lcc) / n:.1f}%).")
    # sample sources (with replacement allowed) and one random target per source
    srcs = rng.choice(lcc, size=pairs_n, replace=True)
    tgts = rng.choice(lcc, size=pairs_n, replace=True)
    uniq_src = np.unique(srcs)
    D = shortest_path(A, directed=False, unweighted=True, indices=uniq_src)
    pos = {s: i for i, s in enumerate(uniq_src)}
    dists = [D[pos[s], t] for s, t in zip(srcs, tgts) if s != t]
    dists = np.array(dists)
    finite = dists[np.isfinite(dists)]
    c = Counter(int(d) for d in finite)
    emit(f"Sampled {len(dists):,} random pairs inside the largest component "
         f"(mean path length {finite.mean():.2f}, median {np.median(finite):.0f}, "
         f"max {int(finite.max())}).")
    emit()
    table(["path length", "pairs", "share", "cumulative"],
          [(k, c[k], f"{100 * c[k] / len(dists):.1f}%",
            f"{100 * sum(c[j] for j in c if j <= k) / len(dists):.1f}%") for k in sorted(c)])
    return {"nodes": n, "lcc": int(len(lcc)), "mean": float(finite.mean())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--pairs", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--us-only", action="store_true",
                    help="drop nodes that came only from the S. Ct. extension volumes")
    ap.add_argument("--include-orders", action="store_true",
                    help="keep order-like nodes (<300 words: cert denials, summary orders) in the graph")
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    random.seed(args.seed)

    nodes = {}
    with open(os.path.join(args.data, "scotus_nodes.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if args.us_only and r["source_reporter"] != "us":
                continue
            nodes[int(r["cap_case_id"])] = r
    G = nx.DiGraph()
    G.add_nodes_from(nodes)
    n_edge_rows = 0
    with open(os.path.join(args.data, "scotus_edges.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            a, b = int(r["citing_cap_id"]), int(r["cited_cap_id"])
            if a in nodes and b in nodes:
                G.add_edge(a, b, weight=int(r["weight"]))
                n_edge_rows += 1

    emit("# CAP SCOTUS citation graph: statistics")
    emit()
    emit(f"Source: `{args.data}` (us-only={args.us_only}, include-orders={args.include_orders}, "
         f"seed={args.seed}, pairs={args.pairs})")
    emit()
    orders = [n for n in G if nodes[n]["is_order_like"] == "1"]
    emit(f"Nodes in file: {G.number_of_nodes():,}; order-like nodes (<300 words: cert denials, summary orders): "
         f"{len(orders):,}; edges: {G.number_of_edges():,}.")
    if not args.include_orders:
        G.remove_nodes_from(orders)
        emit(f"After dropping order-like nodes: {G.number_of_nodes():,} nodes, "
             f"{G.number_of_edges():,} edges.")
    isolated = [n for n in G if G.degree(n) == 0]
    emit(f"Isolated nodes (degree 0): {len(isolated):,}.")
    years = Counter(nodes[n]["year"][:3] + "0s" for n in G if nodes[n]["year"])
    emit()
    emit("## Nodes by decade")
    emit()
    table(["decade", "cases"], sorted(years.items()))

    indeg = dict(G.in_degree())
    outdeg = dict(G.out_degree())
    emit("## Degree distributions")
    emit()
    emit("In-degree (times cited by another SCOTUS case in the graph):")
    emit()
    table(["in-degree", "nodes", "share"], degree_hist(list(indeg.values()), DEG_BINS))
    emit("Out-degree (distinct SCOTUS cases cited):")
    emit()
    table(["out-degree", "nodes", "share"], degree_hist(list(outdeg.values()), DEG_BINS))
    iv = np.array(list(indeg.values())); ov = np.array(list(outdeg.values()))
    emit(f"Mean in-degree {iv.mean():.2f} (median {np.median(iv):.0f}, max {iv.max()}); "
         f"mean out-degree {ov.mean():.2f} (median {np.median(ov):.0f}, max {ov.max()}).")
    emit()

    emit("## Top 40 most-cited cases (in-degree within the SCOTUS graph)")
    emit()
    top = sorted(indeg.items(), key=lambda kv: -kv[1])[:40]
    table(["rank", "case", "cite", "year", "in-degree", "out-degree"],
          [(i + 1, nodes[n]["case_name"], nodes[n]["us_cite"] or nodes[n]["sct_cite"],
            nodes[n]["year"], d, outdeg[n]) for i, (n, d) in enumerate(top)])

    emit("## Sanity checks")
    emit()
    by_cite = {}
    for n, r in nodes.items():
        for k in ("us_cite", "sct_cite"):
            if r[k]:
                by_cite[r[k].replace(" ", "")] = n
    rows = []
    for name, cite in SANITY:
        n = by_cite.get(cite.replace(" ", ""))
        if n is None or n not in G:
            rows.append((name, cite, "MISSING", "", "", ""))
        else:
            rows.append((name, cite, nodes[n]["case_name"], nodes[n]["decision_date"],
                         indeg[n], outdeg[n]))
    table(["expected", "cite", "found as", "decided", "in-degree", "out-degree"], rows)

    emit("## Connectivity and shortest paths (undirected)")
    emit()
    U = G.to_undirected()
    wcc = max(nx.weakly_connected_components(G), key=len)
    emit(f"Largest weakly connected component: {len(wcc):,} of {G.number_of_nodes():,} nodes "
         f"({100 * len(wcc) / G.number_of_nodes():.1f}%).")
    emit()
    results = {}
    results["full"] = path_distribution(U, args.pairs, rng, "Full graph")
    deg_sorted = sorted(U.degree(), key=lambda kv: -kv[1])
    for k in (20, 100):
        hubs = [n for n, _ in deg_sorted[:k]]
        U2 = U.copy()
        U2.remove_nodes_from(hubs)
        U2.remove_nodes_from([n for n in U2 if U2.degree(n) == 0])
        emit(f"### Top {k} hubs removed (by undirected degree; lowest removed degree "
             f"{deg_sorted[k - 1][1]}; isolated leftovers dropped)")
        emit()
        results[f"minus{k}"] = path_distribution(U2, args.pairs, rng, f"Top-{k} hubs removed")

    emit("## Summary")
    emit()
    table(["graph", "nodes", "largest component", "mean path length"],
          [(k, f"{v['nodes']:,}", f"{v['lcc']:,}", f"{v['mean']:.2f}") for k, v in results.items()])

    suffix = "_us_only" if args.us_only else ""
    out = os.path.join(args.data, f"graph_stats{suffix}.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines) + "\n")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()

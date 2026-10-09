#!/usr/bin/env python
"""Statistics for the SCOTUS citation graph built by build_scotus_graph.py.

Run with:
  python -I scripts/graph_stats.py --data data/courtlistener --pairs 2000 --seed 1 [--md notes/graph_stats.md]

Reports node/edge counts, degree distributions, top-cited cases (within SCOTUS and across all courts),
largest weakly connected component, and shortest-path-length distributions over random node pairs in
the undirected graph: full graph, minus the top-20 hubs, minus the top-100 hubs (hubs = highest
SCOTUS in-degree). Requires networkx (pip install networkx).
"""
import argparse
import collections
import csv
import os
import random
import statistics
import sys

import networkx as nx

csv.field_size_limit(1 << 30)


def read_csv(path):
    with open(path, encoding='utf-8', newline='') as f:
        r = csv.reader(f)
        header = next(r)
        for row in r:
            yield dict(zip(header, row))


def pct(n, d):
    return f'{100.0 * n / d:.1f}%' if d else 'n/a'


def table(headers, rows):
    out = ['| ' + ' | '.join(headers) + ' |', '|' + '|'.join('---' for _ in headers) + '|']
    for r in rows:
        out.append('| ' + ' | '.join(str(x) for x in r) + ' |')
    return '\n'.join(out)


def degree_table(values, label):
    bins = [(0, 0), (1, 1), (2, 2), (3, 5), (6, 10), (11, 20), (21, 50), (51, 100), (101, 500), (501, 10 ** 9)]
    c = collections.Counter()
    for v in values:
        for lo, hi in bins:
            if lo <= v <= hi:
                c[(lo, hi)] += 1
                break
    n = len(values)
    rows = [(f'{lo}' if lo == hi else (f'{lo}+' if hi >= 10 ** 9 else f'{lo}-{hi}'), c[(lo, hi)], pct(c[(lo, hi)], n))
            for lo, hi in bins]
    return table([label, 'nodes', 'share'], rows)


def path_length_distribution(G, pairs, rng, label):
    nodes = list(G.nodes)
    lengths = []
    unreachable = 0
    for _ in range(pairs):
        a, b = rng.sample(nodes, 2)
        try:
            lengths.append(nx.shortest_path_length(G, a, b))
        except nx.NetworkXNoPath:
            unreachable += 1
    c = collections.Counter(lengths)
    rows = [(k, c[k], pct(c[k], pairs)) for k in sorted(c)]
    rows.append(('unreachable', unreachable, pct(unreachable, pairs)))
    summary = ''
    if lengths:
        summary = (f'reachable pairs: {len(lengths)}/{pairs}; mean {statistics.mean(lengths):.2f}, '
                   f'median {statistics.median(lengths):.0f}, max {max(lengths)}')
    return f'### Shortest path lengths ({label})\n\n{summary}\n\n' + table(['path length', 'pairs', 'share'], rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--pairs', type=int, default=2000)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--md', help='also write the report to this markdown file')
    ap.add_argument('--suffix', default='', help="e.g. '_merged' to analyze scotus_nodes_merged/scotus_edges_merged")
    a = ap.parse_args()
    rng = random.Random(a.seed)

    nodes = {r['cluster_id']: r for r in read_csv(os.path.join(a.data, f'scotus_nodes{a.suffix}.csv'))}
    G = nx.DiGraph()
    for r in read_csv(os.path.join(a.data, f'scotus_edges{a.suffix}.csv')):
        G.add_edge(r['citing_cluster_id'], r['cited_cluster_id'], depth=int(r['depth']))
    out = []
    p = out.append

    p('# SCOTUS citation graph stats\n')
    n_nodes_all = len(nodes)
    n_mapped = sum(1 for r in nodes.values() if r['opinion_ids'])
    p(f'- SCOTUS clusters (nodes file): {n_nodes_all:,}; with at least one mapped opinion: {n_mapped:,}')
    p(f'- Nodes that appear in at least one SCOTUS->SCOTUS edge: {G.number_of_nodes():,}')
    p(f'- SCOTUS->SCOTUS cluster-level edges: {G.number_of_edges():,} (self-cites excluded)')
    isolated = n_mapped - G.number_of_nodes()
    p(f'- Mapped clusters with no SCOTUS edges at all (isolated; mostly cert denials/orders): {isolated:,}')
    years = collections.Counter(r['year'][:3] + '0s' for r in nodes.values() if r['year'])
    p('- Nodes by decade: ' + ', '.join(f'{k}: {v:,}' for k, v in sorted(years.items())))

    indeg = dict(G.in_degree())
    outdeg = dict(G.out_degree())
    p('\n## Degree distribution (within the SCOTUS->SCOTUS graph)\n')
    p(degree_table(list(indeg.values()), 'in-degree'))
    p('')
    p(degree_table(list(outdeg.values()), 'out-degree'))
    p(f'\nMean in/out degree: {statistics.mean(indeg.values()):.2f}; median in-degree: '
      f'{statistics.median(indeg.values()):.0f}; median out-degree: {statistics.median(outdeg.values()):.0f}')

    def name(c):
        r = nodes.get(c, {})
        return f"{r.get('case_name', '?')[:60]} ({r.get('us_cite') or r.get('year', '')})"

    top = sorted(indeg.items(), key=lambda kv: -kv[1])[:40]
    p('\n## Top 40 most-cited SCOTUS cases within the SCOTUS graph (distinct citing clusters)\n')
    p(table(['rank', 'cluster_id', 'case', 'cited by SCOTUS clusters', 'cited by opinions, all courts', 'CL citation_count'],
            [(i + 1, c, name(c), d, nodes[c]['indeg_all_courts'], nodes[c]['citation_count']) for i, (c, d) in enumerate(top)]))

    top_all = sorted(((int(r['indeg_all_courts'] or 0), c) for c, r in nodes.items()), reverse=True)[:40]
    p('\n## Top 40 most-cited SCOTUS cases across all courts (citing opinions in the full citation map)\n')
    p(table(['rank', 'cluster_id', 'case', 'citing opinions, all courts', 'SCOTUS in-degree', 'CL citation_count'],
            [(i + 1, c, name(c), d, indeg.get(c, 0), nodes[c]['citation_count']) for i, (d, c) in enumerate(top_all)]))

    U = G.to_undirected()
    comps = sorted(nx.connected_components(U), key=len, reverse=True)
    p(f'\n## Connectivity\n\n- Weakly connected components: {len(comps):,}; largest has {len(comps[0]):,} nodes '
      f'({pct(len(comps[0]), U.number_of_nodes())} of non-isolated nodes); next sizes: {[len(c) for c in comps[1:6]]}')

    p(f'\n## Path lengths (undirected, {a.pairs} random pairs, seed {a.seed})\n')
    p(path_length_distribution(U, a.pairs, rng, 'full graph'))
    hubs = [c for c, _ in sorted(indeg.items(), key=lambda kv: -kv[1])]
    for k in (20, 100):
        H = U.copy()
        H.remove_nodes_from(hubs[:k])
        comps_k = sorted(nx.connected_components(H), key=len, reverse=True)
        p(f'\nAfter removing top {k} hubs: {H.number_of_nodes():,} nodes, {H.number_of_edges():,} edges, '
          f'largest component {len(comps_k[0]):,} ({pct(len(comps_k[0]), H.number_of_nodes())})\n')
        p(path_length_distribution(H, a.pairs, rng, f'top {k} hubs removed'))

    p('\n## Sanity check: well-known cases\n')
    checks = [('Twombly', '550 U.S. 544'), ('Iqbal', '556 U.S. 662'), ('Celotex', '477 U.S. 317'),
              ('Liberty Lobby', '477 U.S. 242'), ('Chevron', '467 U.S. 837'), ('Erie', '304 U.S. 64'),
              ('Marbury', '5 U.S. 137'), ('Brown v. Board', '347 U.S. 483')]
    rows = []
    for label, cite in checks:
        hits = [r for r in nodes.values() if r['us_cite'] == cite]
        if not hits:
            rows.append((label, cite, 'NOT FOUND', '', '', '', ''))
        for r in hits:
            c = r['cluster_id']
            rows.append((label, cite, c, r['case_name'][:50], indeg.get(c, 0), outdeg.get(c, 0), r['indeg_all_courts']))
    p(table(['case', 'cite', 'cluster_id', 'name in CL', 'SCOTUS in-degree', 'SCOTUS out-degree', 'in-degree all courts'], rows))

    text = '\n'.join(out)
    print(text)
    if a.md:
        with open(a.md, 'w', encoding='utf-8') as f:
            f.write(text + '\n')
        print(f'\n(wrote {a.md})', file=sys.stderr)


if __name__ == '__main__':
    main()

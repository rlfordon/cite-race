#!/usr/bin/env python
"""Build a SCOTUS-only citation graph from CourtListener bulk data.

Run with:
  python -I scripts/build_scotus_graph.py --raw data/courtlistener/raw --out data/courtlistener --date 2026-09-30

Stages (each writes a file under --out and is skipped if the file exists, unless --force):
  1. dockets   : stream dockets-<date>.csv.bz2          -> scotus_dockets.csv   (court_id == 'scotus')
  2. clusters  : stream opinion-clusters-<date>.csv.bz2 -> scotus_clusters.csv  (docket_id in scotus dockets)
  3. citations : stream citations-<date>.csv.bz2        -> scotus_citations.csv (reporter cites for scotus clusters)
  4. opmap     : scotus_caption_data*.csv (from bulk-data/randoms/) -> scotus_opinion_map.csv (opinion_id -> cluster_id)
                 plus optional raw/scotus_opinion_map_supplement.csv (opinion_id,cluster_id) for gap fill
  5. edges     : stream citation-map-<date>.csv.bz2     -> scotus_edges.csv, scotus_out_edges_all.csv, scotus_indegree_all.csv
  6. nodes     : join 2-5                                -> scotus_nodes.csv

The bulk CSVs are PostgreSQL COPY ... (FORMAT csv, ESCAPE '\\', HEADER): fields quoted with ", a quote inside a
field is escaped as \\", NULL is written as nothing between commas, empty string as "". Fields may contain newlines.
Decompression is streamed through an external `bzip2 -dc` process; nothing is extracted to disk.
"""
import argparse
import collections
import csv
import glob
import io
import os
import subprocess
import sys
import time

csv.field_size_limit(1 << 30)


def log(msg):
    print(time.strftime('%H:%M:%S'), msg, file=sys.stderr, flush=True)


def bz2_rows(path):
    """Yield csv rows (header first) from a .bz2 file via a streaming `bzip2 -dc` subprocess."""
    proc = subprocess.Popen(['bzip2', '-dc', path], stdout=subprocess.PIPE, bufsize=1 << 20)
    text = io.TextIOWrapper(proc.stdout, encoding='utf-8', errors='replace', newline='')
    reader = csv.reader(text, escapechar='\\', doublequote=False, strict=False)
    for row in reader:
        yield row
    proc.stdout.close()
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f'bzip2 exited with {rc} for {path}')


def write_csv(path, header, rows):
    tmp = path + '.tmp'
    n = 0
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
            n += 1
    os.replace(tmp, path)
    log(f'wrote {path} ({n:,} rows)')
    return n


def read_csv(path):
    with open(path, encoding='utf-8', newline='') as f:
        r = csv.reader(f)
        header = next(r)
        for row in r:
            yield dict(zip(header, row))


# ---------------------------------------------------------------- stage 1
def stage_dockets(raw, out, date, force):
    dst = os.path.join(out, 'scotus_dockets.csv')
    if os.path.exists(dst) and not force:
        log(f'skip dockets ({dst} exists)')
        return
    src = os.path.join(raw, f'dockets-{date}.csv.bz2')
    log(f'stream {src}')
    it = bz2_rows(src)
    header = next(it)
    ix = {h: i for i, h in enumerate(header)}
    c_id, c_court = ix['id'], ix['court_id']
    c_num, c_name, c_filed = ix['docket_number'], ix['case_name'], ix['date_filed']

    def rows():
        n = 0
        for row in it:
            n += 1
            if n % 5_000_000 == 0:
                log(f'  dockets rows scanned: {n:,}')
            if len(row) > c_court and row[c_court] == 'scotus':
                yield (row[c_id], row[c_num], row[c_name], row[c_filed])
        log(f'  dockets rows scanned: {n:,}')

    write_csv(dst, ['docket_id', 'docket_number', 'case_name', 'date_filed'], rows())


# ---------------------------------------------------------------- stage 2
def stage_clusters(raw, out, date, force):
    dst = os.path.join(out, 'scotus_clusters.csv')
    if os.path.exists(dst) and not force:
        log(f'skip clusters ({dst} exists)')
        return
    dockets = {r['docket_id'] for r in read_csv(os.path.join(out, 'scotus_dockets.csv'))}
    log(f'{len(dockets):,} scotus dockets')
    src = os.path.join(raw, f'opinion-clusters-{date}.csv.bz2')
    log(f'stream {src}')
    it = bz2_rows(src)
    header = next(it)
    ix = {h: i for i, h in enumerate(header)}
    keep = ['id', 'docket_id', 'case_name', 'case_name_short', 'case_name_full', 'date_filed',
            'date_filed_is_approximate', 'scdb_id', 'citation_count', 'precedential_status', 'source', 'slug', 'blocked']
    ki = [ix[k] for k in keep]
    c_docket = ix['docket_id']

    def rows():
        n = 0
        for row in it:
            n += 1
            if n % 2_000_000 == 0:
                log(f'  cluster rows scanned: {n:,}')
            if len(row) > c_docket and row[c_docket] in dockets:
                yield [row[i] for i in ki]
        log(f'  cluster rows scanned: {n:,}')

    write_csv(dst, keep, rows())


# ---------------------------------------------------------------- stage 3
def stage_citations(raw, out, date, force):
    dst = os.path.join(out, 'scotus_citations.csv')
    if os.path.exists(dst) and not force:
        log(f'skip citations ({dst} exists)')
        return
    clusters = {r['id'] for r in read_csv(os.path.join(out, 'scotus_clusters.csv'))}
    src = os.path.join(raw, f'citations-{date}.csv.bz2')
    log(f'stream {src}')
    it = bz2_rows(src)
    header = next(it)
    ix = {h: i for i, h in enumerate(header)}

    def rows():
        for row in it:
            if len(row) > ix['cluster_id'] and row[ix['cluster_id']] in clusters:
                yield (row[ix['cluster_id']], row[ix['volume']], row[ix['reporter']], row[ix['page']], row[ix['type']])

    write_csv(dst, ['cluster_id', 'volume', 'reporter', 'page', 'type'], rows())


# ---------------------------------------------------------------- stage 4
def stage_opmap(raw, out, date, force):
    dst = os.path.join(out, 'scotus_opinion_map.csv')
    if os.path.exists(dst) and not force:
        log(f'skip opmap ({dst} exists)')
        return
    clusters = {r['id'] for r in read_csv(os.path.join(out, 'scotus_clusters.csv'))}
    caps = sorted(glob.glob(os.path.join(raw, 'scotus_caption_data*.csv')))
    if not caps:
        raise SystemExit('need bulk-data/randoms/scotus_caption_data.csv in the raw dir')
    log(f'reading {caps[-1]}')
    pairs = {}
    not_scotus = 0
    with open(caps[-1], encoding='utf-8', errors='replace', newline='') as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            if len(row) < 2 or not row[0].strip():
                continue
            op, cl = row[0].strip(), row[1].strip()
            if not op.isdigit() or not cl.isdigit():
                continue
            if cl in clusters:
                pairs[op] = cl
            else:
                not_scotus += 1
    supp = os.path.join(raw, 'scotus_opinion_map_supplement.csv')
    nsupp = 0
    if os.path.exists(supp):
        for r in read_csv(supp):
            if r['cluster_id'] in clusters:
                pairs[r['opinion_id']] = r['cluster_id']
                nsupp += 1
    covered = set(pairs.values())
    missing = clusters - covered
    log(f'opinion map: {len(pairs):,} opinions -> {len(covered):,} clusters; caption rows whose cluster is not in the '
        f'current scotus set: {not_scotus:,}; supplement rows: {nsupp:,}; scotus clusters with NO opinion mapping: {len(missing):,}')
    write_csv(dst, ['opinion_id', 'cluster_id'], sorted(pairs.items(), key=lambda kv: int(kv[0])))
    write_csv(os.path.join(out, 'scotus_clusters_unmapped.csv'), ['cluster_id'], ((c,) for c in sorted(missing, key=int)))


# ---------------------------------------------------------------- stage 5
def stage_edges(raw, out, date, force):
    dst = os.path.join(out, 'scotus_edges.csv')
    if os.path.exists(dst) and not force:
        log(f'skip edges ({dst} exists)')
        return
    opmap = {int(r['opinion_id']): int(r['cluster_id']) for r in read_csv(os.path.join(out, 'scotus_opinion_map.csv'))}
    src = os.path.join(raw, f'citation-map-{date}.csv.bz2')
    log(f'stream {src} with {len(opmap):,} mapped scotus opinions')
    it = bz2_rows(src)
    header = next(it)
    ix = {h: i for i, h in enumerate(header)}
    c_depth, c_cited, c_citing = ix['depth'], ix['cited_opinion_id'], ix['citing_opinion_id']
    edges = collections.defaultdict(lambda: [0, 0])   # (citing_cl, cited_cl) -> [depth_sum, opinion_pairs]
    indeg_rows = collections.Counter()                  # cited_cl -> citing opinions from any court
    indeg_scotus_rows = collections.Counter()           # cited_cl -> citing scotus opinions
    all_path = os.path.join(out, 'scotus_out_edges_all.csv')
    out_all = open(all_path + '.tmp', 'w', encoding='utf-8', newline='')
    w_all = csv.writer(out_all)
    w_all.writerow(['citing_cluster_id', 'citing_opinion_id', 'cited_opinion_id', 'cited_cluster_id_if_scotus', 'depth'])
    n = n_out = n_in = n_both = n_self = 0
    for row in it:
        n += 1
        if n % 10_000_000 == 0:
            log(f'  citation-map rows: {n:,}')
        try:
            citing = int(row[c_citing])
            cited = int(row[c_cited])
            depth = int(row[c_depth] or 1)
        except (ValueError, IndexError):
            continue
        ccl = opmap.get(citing)
        dcl = opmap.get(cited)
        if dcl is not None:
            n_in += 1
            indeg_rows[dcl] += 1
        if ccl is not None:
            n_out += 1
            w_all.writerow([ccl, citing, cited, dcl if dcl is not None else '', depth])
            if dcl is not None:
                indeg_scotus_rows[dcl] += 1
                if ccl == dcl:
                    n_self += 1
                else:
                    n_both += 1
                    e = edges[(ccl, dcl)]
                    e[0] += depth
                    e[1] += 1
    out_all.close()
    os.replace(all_path + '.tmp', all_path)
    log(f'citation-map rows: {n:,}; rows with scotus citer: {n_out:,}; rows with scotus cited: {n_in:,}; '
        f'scotus->scotus rows: {n_both:,} (+{n_self:,} intra-cluster self cites dropped); cluster edges: {len(edges):,}')
    write_csv(dst, ['citing_cluster_id', 'cited_cluster_id', 'depth', 'opinion_pairs'],
              ((a, b, v[0], v[1]) for (a, b), v in sorted(edges.items())))
    write_csv(os.path.join(out, 'scotus_indegree_all.csv'),
              ['cluster_id', 'citing_opinions_all_courts', 'citing_opinions_scotus'],
              ((c, indeg_rows[c], indeg_scotus_rows.get(c, 0)) for c in sorted(indeg_rows)))


# ---------------------------------------------------------------- stage 6
def stage_nodes(raw, out, date, force):
    dst = os.path.join(out, 'scotus_nodes.csv')
    if os.path.exists(dst) and not force:
        log(f'skip nodes ({dst} exists)')
        return
    ops = collections.defaultdict(list)
    for r in read_csv(os.path.join(out, 'scotus_opinion_map.csv')):
        ops[r['cluster_id']].append(r['opinion_id'])
    cites = collections.defaultdict(list)
    for r in read_csv(os.path.join(out, 'scotus_citations.csv')):
        cites[r['cluster_id']].append((r['volume'], r['reporter'], r['page'], r['type']))
    indeg = {r['cluster_id']: r for r in read_csv(os.path.join(out, 'scotus_indegree_all.csv'))}

    def pick_us(lst):
        us = [c for c in lst if c[1] == 'U.S.']
        if us:
            v, _, p, _ = us[0]
            return f'{v} U.S. {p}'
        return ''

    def rows():
        for r in read_csv(os.path.join(out, 'scotus_clusters.csv')):
            cid = r['id']
            lst = cites.get(cid, [])
            d = indeg.get(cid, {})
            yield [cid, ';'.join(sorted(ops.get(cid, []), key=int)),
                   r['case_name'] or r['case_name_full'] or r['case_name_short'],
                   pick_us(lst), ' | '.join(f'{v} {rp} {p}' for v, rp, p, _ in lst),
                   r['date_filed'], (r['date_filed'] or '')[:4], r['citation_count'],
                   d.get('citing_opinions_all_courts', 0), d.get('citing_opinions_scotus', 0),
                   r['precedential_status'], r['scdb_id'], r['docket_id']]

    write_csv(dst, ['cluster_id', 'opinion_ids', 'case_name', 'us_cite', 'all_cites', 'date_filed', 'year',
                    'citation_count', 'indeg_all_courts', 'indeg_scotus', 'precedential_status', 'scdb_id', 'docket_id'],
              rows())


# ---------------------------------------------------------------- stage 7
_STOP = {'v', 'vs', 'the', 'of', 'and', 'co', 'inc', 'corp', 'et', 'al', 'a', 'an', 'in', 're', 'ex', 'parte',
         'state', 'states', 'united', 'company', 'city', 'county', 'no', 'on', 'for', 'by', 'to', 'at', 'ltd', 'llc'}


def _tokens(name):
    import re
    return {t for t in re.findall(r'[a-z0-9]+', (name or '').lower()) if t not in _STOP and len(t) > 1}


def stage_merge(raw, out, date, force):
    """Collapse duplicate clusters (same U.S. cite + same date_filed + overlapping case-name tokens).

    CourtListener holds many SCOTUS cases twice (older import and Harvard/CAP import, or slip opinion and
    bound volume). A page of U.S. Reports can also hold several distinct orders, so the cite alone is not
    enough. Canonical id = the member with the most SCOTUS edges (ties: lowest id)."""
    dst = os.path.join(out, 'scotus_edges_merged.csv')
    if os.path.exists(dst) and not force:
        log(f'skip merge ({dst} exists)')
        return
    nodes = {r['cluster_id']: r for r in read_csv(os.path.join(out, 'scotus_nodes.csv'))}
    edges = list(read_csv(os.path.join(out, 'scotus_edges.csv')))
    deg = collections.Counter()
    for e in edges:
        deg[e['citing_cluster_id']] += 1
        deg[e['cited_cluster_id']] += 1
    groups = collections.defaultdict(list)
    for c, r in nodes.items():
        if r['us_cite'] and deg[c]:
            groups[r['us_cite']].append(c)
    canon = {}
    merged_groups = 0
    for cite, members in groups.items():
        if len(members) < 2:
            continue
        members = sorted(members, key=lambda c: (-deg[c], int(c)))
        used = set()
        for i, a in enumerate(members):
            if a in used:
                continue
            group = [a]
            for b in members[i + 1:]:
                if b in used:
                    continue
                ra, rb = nodes[a], nodes[b]
                same_date = ra['date_filed'] == rb['date_filed'] or (ra['year'] and ra['year'] == rb['year'])
                ta, tb = _tokens(ra['case_name']), _tokens(rb['case_name'])
                overlap = len(ta & tb) / max(1, min(len(ta), len(tb))) if ta and tb else 0.0
                if same_date and overlap >= 0.5:
                    group.append(b)
                    used.add(b)
            if len(group) > 1:
                merged_groups += 1
                for b in group[1:]:
                    canon[b] = a
    log(f'merge: {merged_groups:,} duplicate groups, {len(canon):,} clusters folded into a canonical cluster')
    agg = collections.defaultdict(lambda: [0, 0])
    dropped = 0
    for e in edges:
        a = canon.get(e['citing_cluster_id'], e['citing_cluster_id'])
        b = canon.get(e['cited_cluster_id'], e['cited_cluster_id'])
        if a == b:
            dropped += 1
            continue
        v = agg[(a, b)]
        v[0] += int(e['depth'])
        v[1] += int(e['opinion_pairs'])
    log(f'merge: {len(edges):,} edges -> {len(agg):,} (dropped {dropped:,} that became self-loops)')
    write_csv(dst, ['citing_cluster_id', 'cited_cluster_id', 'depth', 'opinion_pairs'],
              ((a, b, v[0], v[1]) for (a, b), v in sorted(agg.items(), key=lambda kv: (int(kv[0][0]), int(kv[0][1])))))
    folded = collections.defaultdict(list)
    for b, a in canon.items():
        folded[a].append(b)
    header = list(next(iter(nodes.values())).keys()) + ['merged_cluster_ids']

    def rows():
        for c, r in nodes.items():
            if c in canon:
                continue
            extra = folded.get(c, [])
            r = dict(r)
            if extra:
                r['opinion_ids'] = ';'.join(sorted({o for x in [c] + extra for o in nodes[x]['opinion_ids'].split(';') if o}, key=int))
                r['indeg_all_courts'] = sum(int(nodes[x]['indeg_all_courts'] or 0) for x in [c] + extra)
                r['indeg_scotus'] = sum(int(nodes[x]['indeg_scotus'] or 0) for x in [c] + extra)
                r['citation_count'] = sum(int(nodes[x]['citation_count'] or 0) for x in [c] + extra)
            yield [r[h] for h in header[:-1]] + [';'.join(sorted(extra, key=int))]

    write_csv(os.path.join(out, 'scotus_nodes_merged.csv'), header, rows())
    write_csv(os.path.join(out, 'scotus_cluster_merge_map.csv'), ['cluster_id', 'canonical_cluster_id'],
              sorted(canon.items(), key=lambda kv: int(kv[0])))


STAGES = [('dockets', stage_dockets), ('clusters', stage_clusters), ('citations', stage_citations),
          ('opmap', stage_opmap), ('edges', stage_edges), ('nodes', stage_nodes), ('merge', stage_merge)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--date', required=True)
    ap.add_argument('--only', help='comma-separated list of stages to run')
    ap.add_argument('--force', action='store_true', help='recompute even if output exists')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    only = set(a.only.split(',')) if a.only else None
    for name, fn in STAGES:
        if only and name not in only:
            continue
        log(f'=== stage {name}')
        fn(a.raw, a.out, a.date, a.force)


if __name__ == '__main__':
    main()

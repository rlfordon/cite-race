# SCOTUS citation graph from CourtListener bulk data

Goal: a Supreme-Court-only citation graph (which SCOTUS opinions cite which other SCOTUS opinions) for the
classroom "citation race" game, built from Free Law Project bulk dumps with **zero CourtListener API calls**.

Built 2026-10-08 from the 2026-09-30 quarterly dump.

## Where the bulk data lives

- Help page: `https://www.courtlistener.com/help/api/bulk-data/` (now redirects to
  `https://wiki.free.law/c/courtlistener/help/api/bulk-data/bulk-legal-data`).
- Public S3 bucket `com-courtlistener-storage`, prefix `bulk-data/`. List it with plain curl (no auth):
  `curl "https://com-courtlistener-storage.s3-us-west-2.amazonaws.com/?list-type=2&prefix=bulk-data/&max-keys=1000"`
  (1,111 keys; the listing is truncated at 1000, so follow `NextContinuationToken`).
- Dumps are regenerated quarterly (last day of Mar/Jun/Sep/Dec, 3 AM PST). Files are named
  `<table>-<YYYY-MM-DD>.csv.bz2`. Dates present as of 2026-10-08: 2025-09-04 ... 2026-06-30, 2026-09-30.
- The per-dump `load-bulk-data-<date>.sh` lists the exact column order for every CSV (it is the `psql \COPY`
  script), and `schema-<date>.sql` has the full PostgreSQL DDL. Both are tiny and were downloaded.

## Files used (all from the 2026-09-30 dump unless noted)

| file | S3 size | table (`load-bulk-data` name) | used for |
|---|---|---|---|
| `citation-map-2026-09-30.csv.bz2` | 533 MB | `search_opinionscited(id, depth, cited_opinion_id, citing_opinion_id)` | the edges (opinion -> opinion) |
| `citations-2026-09-30.csv.bz2` | 127 MB | `search_citation(id, volume, reporter, page, type, cluster_id, date_created, date_modified)` | reporter cites ("550 U.S. 544") per cluster |
| `opinion-clusters-2026-09-30.csv.bz2` | 2.47 GB | `search_opinioncluster(id, ..., case_name, ..., date_filed, ..., citation_count, precedential_status, ..., docket_id, ...)` 36 columns | node metadata; `docket_id` links to the court |
| `dockets-2026-09-30.csv.bz2` | 5.14 GB | `search_docket(id, ..., court_id, ...)` 54 columns | the SCOTUS filter (`court_id == 'scotus'`) |
| `courts-2026-09-30.csv.bz2` | 81 KB | `search_court` | confirms the court id `scotus` |
| `bulk-data/randoms/scotus_caption_data.csv` | 244 MB, S3 Last-Modified 2025-07-28 | undocumented one-off export: `opinion_id, cluster_id, docket_id, docket_number, case_name, citations, date_filed, date_filed_is_approximate, opinion_type` | the **opinion_id -> cluster_id map for SCOTUS**, which is the one thing the big tables cannot give you without the opinions dump |
| `load-bulk-data-2026-09-30.sh`, `schema-2026-09-30.sql` | 19 KB, 555 KB | - | schema reference |

Not downloaded: `opinions-2026-09-30.csv.bz2` is **55.3 GB** compressed (full opinion text in several formats
per row), far over the budget. It is the only regular table that carries `opinion.id -> cluster_id`.

Also present but unused: `bulk-data/randoms/scotus_network.csv` (7 MB, 2024-04-04): an older
`id, citing_opinion_id, cited_opinion_id, depth` export with 262k edges among ~25k SCOTUS opinions. It is a
subset of what the current citation map gives, and undated as to coverage, so it was only used as a cross-check.

Total downloaded: ~8.6 GB.

## Why the SCOTUS filter is awkward, and how it was done

The citation map is keyed by **opinion** id, but court membership hangs off the **docket**
(`docket.court_id`), via `cluster.docket_id`. The chain is
`opinion.cluster_id -> cluster.docket_id -> docket.court_id`, and the first hop lives only in the 55 GB
opinions table (where `cluster_id` is the last of 22 columns, after the full text).

Things that do not work:
- Assuming `opinion.id == cluster.id`. True for only 12% of SCOTUS opinions (the pre-2016 imports); the
  Harvard/CAP-era imports have unrelated ids.
- The API. The v4 docs now state a default throttle of 5 requests/minute, 50/hour, 125/day, and pages are
  20 items, so enumerating ~500k SCOTUS opinions is out of the question.

What works: Free Law Project left `bulk-data/randoms/scotus_caption_data.csv` in the bucket. It is a SCOTUS-only
export of 521,306 opinions with their cluster ids (499,018 clusters), dated July 2025. Pipeline:

1. `dockets` dump, streamed: keep rows with `court_id == 'scotus'` -> `scotus_dockets.csv`.
2. `opinion-clusters` dump, streamed: keep rows whose `docket_id` is a SCOTUS docket -> `scotus_clusters.csv`.
   This is the authoritative, current node set.
3. `citations` dump, streamed: keep rows whose `cluster_id` is in that set -> `scotus_citations.csv`.
4. `scotus_caption_data.csv`: keep `(opinion_id, cluster_id)` pairs whose cluster is in the set ->
   `scotus_opinion_map.csv`. Clusters with no mapped opinion are listed in `scotus_clusters_unmapped.csv`, and
   `raw/scotus_opinion_map_supplement.csv` (same two columns) is merged in if present.

   **The gap and the only API calls made.** 532 of 499,548 SCOTUS clusters were missing from the caption file:
   everything CL added after it was exported, i.e. the 2023-2026 slip opinions scraped from supremecourt.gov
   (source `C`), including Loper Bright, Rahimi, SFFA v. Harvard, Trump v. J.G.G., A.A.R.P. v. Trump; 418
   Published and 114 Relating-to orders; CL counts 17,535 citations to them. Every one has cluster id
   >= 9,493,078 while the caption file tops out at 9,486,335, so a single filtered listing covers them:
   `GET /api/rest/v4/clusters/?docket__court=scotus&id__gte=9493078&fields=id,sub_opinions&order_by=id`,
   paged at 100 = **6 API requests** (made through the CourtListener MCP server; account quota is 5,000/hour).
   The 534 `(cluster, opinion)` pairs returned are in `raw/gapfill_pages.txt` and
   `raw/scotus_opinion_map_supplement.csv`; two of them are clusters newer than the dump and are ignored.
   Each of these clusters has exactly one sub-opinion. After the merge, 0 SCOTUS clusters are unmapped.
   To redo this for a later dump: rerun the build, read `scotus_clusters_unmapped.csv` for the new floor id,
   repeat the listing with that `id__gte`, append to the supplement, rerun `--only opmap,edges,nodes --force`.
5. `citation-map` dump, streamed once: for every row, look up both opinion ids in the map. Produces
   - `scotus_edges.csv` (`citing_cluster_id, cited_cluster_id, depth, opinion_pairs`): SCOTUS -> SCOTUS,
     aggregated to cluster level, intra-cluster self-cites (e.g. a dissent citing its own majority) dropped;
     `depth` is the summed CL depth (number of times cited within the text), `opinion_pairs` the number of
     opinion-level rows that collapsed into the edge.
   - `scotus_out_edges_all.csv`: every row whose citing opinion is SCOTUS, with the cited opinion id and the
     cited cluster id when the target is SCOTUS. Non-SCOTUS targets cannot be resolved to a cluster without the
     opinions dump, so that column is blank for them.
   - `scotus_indegree_all.csv`: for every SCOTUS cluster, the number of citing opinions from **any** court
     (rows in the citation map whose cited opinion maps to the cluster) and from SCOTUS only. This is the
     "times cited anywhere" number. The clusters table also carries CL's own `citation_count`, which is kept
     alongside it in the nodes file.
6. Join everything -> `scotus_nodes.csv`.

## Output files (`data/courtlistener/`)

- `scotus_nodes.csv`: `cluster_id, opinion_ids (;-separated), case_name, us_cite, all_cites, date_filed, year,
  citation_count (CL's), indeg_all_courts, indeg_scotus, precedential_status, scdb_id, docket_id`
- `scotus_edges.csv`: `citing_cluster_id, cited_cluster_id, depth, opinion_pairs`
- `scotus_out_edges_all.csv`, `scotus_indegree_all.csv`, `scotus_opinion_map.csv`, `scotus_clusters.csv`,
  `scotus_citations.csv`, `scotus_dockets.csv`, `scotus_clusters_unmapped.csv` (intermediates, all re-creatable)

## CSV format pitfalls

- The dumps are PostgreSQL `COPY ... (FORMAT csv, ENCODING utf8, ESCAPE '\', HEADER)`. Since the 2025-01-24
  dump fields are quoted with `"` (older dumps used backticks). A quote inside a field is written as `\"`, not
  `""`, so parse with `csv.reader(f, escapechar='\\', doublequote=False)`. Python's default dialect would
  silently mangle any case name containing a quote.
- Fields contain embedded newlines (a third of cluster rows: syllabus/headnotes HTML). Never split on lines;
  always go through a real CSV parser with `newline=''`.
- NULL is written as nothing between commas (`,,`); empty string as `,"",`. Python's csv returns `''` for both.
- Every value is quoted, including integers (`"268508171","3",...`); cast as needed.
- `csv.field_size_limit` must be raised (default 128 KB is too small for cluster rows).
- Streaming: `bzip2 -dc file | python -I script` works; the scripts spawn `bzip2 -dc` as a subprocess so
  nothing is extracted to disk. Single-threaded bzip2 is the bottleneck (~30 MB/s of output).
- `scotus_caption_data.csv` is a sloppy spreadsheet export: a trailing run of empty columns on every row, and
  about 8,000 rows where the fields after `case_name` are shifted by one (unquoted commas). The first two
  columns (`opinion_id, cluster_id`) parse cleanly on all 521,306 rows, and nothing else was taken from it.
- The Bash tool used here collapses backslashes in heredocs; write scripts to files rather than inline.

## How to re-run

```
cd "C:/Users/Rebecca Fordon/Projects/cite-race"
B=https://com-courtlistener-storage.s3-us-west-2.amazonaws.com/bulk-data
D=2026-09-30
for f in courts citations citation-map opinion-clusters dockets; do
  curl -sS -L -C - -o data/courtlistener/raw/$f-$D.csv.bz2 $B/$f-$D.csv.bz2
done
curl -sS -L -C - -o data/courtlistener/raw/scotus_caption_data-2025-07-28.csv $B/randoms/scotus_caption_data.csv
curl -sS -L -C - -o data/courtlistener/raw/load-bulk-data-$D.sh $B/load-bulk-data-$D.sh
curl -sS -L -C - -o data/courtlistener/raw/schema-$D.sql $B/schema-$D.sql

python -I scripts/build_scotus_graph.py --raw data/courtlistener/raw --out data/courtlistener --date $D
python -m pip install networkx
python -I scripts/graph_stats.py --data data/courtlistener --pairs 2000 --seed 1 --md notes/graph_stats.md
```

`build_scotus_graph.py` skips any stage whose output already exists; use `--force` or `--only stage,...`
to redo parts. For a new quarterly dump change `$D`; if a newer `scotus_caption_data.csv` ever appears, drop it in
`raw/` with its date in the name (the script takes the lexically last `scotus_caption_data*.csv`).

Then, for the duplicate-free graph:

```
python -I scripts/build_scotus_graph.py --raw data/courtlistener/raw --out data/courtlistener --date $D --only merge --force
python -I scripts/graph_stats.py --data data/courtlistener --suffix _merged --pairs 2000 --seed 1 --md notes/graph_stats_merged.md
```

Wall-clock on this machine: downloads ~12 min (8.6 GB), dockets stage 14 min, clusters 7 min, citations/opmap
1 min, citation-map pass 2 min, nodes/merge/stats a few minutes each.

## Results (2026-09-30 dump; full tables in `notes/graph_stats.md` and `notes/graph_stats_merged.md`)

### Headline numbers

| | raw clusters | duplicates merged |
|---|---|---|
| SCOTUS clusters (nodes file) | 499,548 | 496,313 |
| mapped opinions | 521,836 | 521,836 |
| clusters that take part in any SCOTUS->SCOTUS edge | 46,737 | 43,155 |
| isolated clusters (cert denials, orders, nothing cited/citing) | 452,811 | 453,158 |
| SCOTUS->SCOTUS edges (cluster level, self-cites dropped) | 325,314 | 304,448 |
| weakly connected components | 2,283 | 1,695 |
| largest component | 41,952 (89.8% of active nodes) | 39,497 (91.5%) |
| mean / median degree (in = out) | 6.96 / 2 | 7.05 / 2 |

The citation map has 78,404,647 opinion->opinion rows in total. 724,467 have a SCOTUS citer; 11,967,111 have
a SCOTUS cited opinion (that is the "cited anywhere" signal, kept per cluster in `indeg_all_courts`).

Only ~9% of SCOTUS clusters are in the graph at all: CL's SCOTUS set is dominated by one-line cert denials and
orders from the U.S. Reports (the 1990s alone hold 115k clusters, of which 2.5k cite anything). **For the game,
use the giant component of the merged graph** (39,497 cases) and ignore the rest.

### Shortest paths (undirected, 2,000 random pairs of active nodes, seed 1)

Raw graph:

| path length | full graph | top 20 hubs removed | top 100 hubs removed |
|---|---|---|---|
| 1 | 0.1% | 0.1% | 0.1% |
| 2 | 0.9% | 0.7% | 0.8% |
| 3 | 10.2% | 8.7% | 7.2% |
| 4 | 28.4% | 26.4% | 26.6% |
| 5 | 26.2% | 26.4% | 24.2% |
| 6 | 9.8% | 9.3% | 9.9% |
| 7 | 2.5% | 1.6% | 1.6% |
| 8-9 | 0.4% | 0.1% | 0.3% |
| unreachable | 21.6% | 26.6% | 29.1% |
| mean / median (reachable) | 4.54 / 4 | 4.55 / 5 | 4.58 / 5 |

Merged graph:

| path length | full graph | top 20 hubs removed | top 100 hubs removed |
|---|---|---|---|
| 1 | 0.1% | 0.1% | 0.0% |
| 2 | 1.2% | 0.8% | 0.7% |
| 3 | 11.1% | 9.6% | 8.1% |
| 4 | 30.8% | 29.0% | 28.2% |
| 5 | 26.4% | 26.3% | 28.4% |
| 6 | 9.7% | 9.2% | 9.7% |
| 7 | 2.5% | 1.8% | 1.9% |
| 8-9 | 0.3% | 0.2% | 0.3% |
| unreachable | 18.1% | 23.1% | 22.8% |
| mean / median (reachable) | 4.50 / 4 | 4.51 / 4 | 4.59 / 5 |

"Unreachable" pairs are almost entirely pairs with one endpoint outside the giant component (8-10% of
active nodes), not long paths; inside the giant component every sampled pair connects in at most 9 hops.
Removing the top 20 or even top 100 hubs barely moves the distribution (mean 4.5 -> 4.6): the small-world
property comes from the bulk of mid-degree cases, not from a few superhubs. So a "no hubs allowed" rule
makes the race harder mainly by removing obvious stepping stones, not by lengthening the optimal path.

### Hubs, and which ones are boilerplate

Top cited within the SCOTUS graph (merged): Detroit Timber & Lumber (990), Gregg v. Georgia (901), Martin v.
D.C. Court of Appeals (604), McCulloch (428), Miranda (297), Booker (295), Marbury (284), Gibbons v. Ogden
(273), Chevron (263), Gideon (252), Boyd (237), Ashwander (227), then Erie, Cantwell, Ex parte Young, NYT v.
Sullivan, Strickland, Brown v. Board, Johnson v. Zerbst, Buckley v. Valeo ...

Three of the top ten are boilerplate, not doctrine, and should be excluded from the game's node set:
- *United States v. Detroit Timber & Lumber Co.*, 200 U.S. 321: cited by every syllabus ("The syllabus
  constitutes no part of the opinion ... See ...").
- *Martin v. District of Columbia Court of Appeals*, 506 U.S. 1, and *Brown v. Herald Co.*, 464 U.S. 928
  (288 raw in-degree): cited in every order denying in forma pauperis status to an abusive filer.
- *Gregg v. Georgia*: a large share of its 900 in-links are the Brennan/Marshall "adhering to our views"
  dissents from cert denials in capital cases, not merits opinions.

Top cited across all courts (the `indeg_all_courts` column): Iqbal 159,004; Twombly 155,785; Anderson v.
Liberty Lobby 138,555; Celotex 122,464; Strickland 119,566; Anders v. California 87,895; Jackson v. Virginia
79,770; Matsushita 60,100; Miranda 57,532; Monell 43,217. These match CL's own `citation_count` to within
rounding, which confirms the opinion->cluster mapping is right.

### Sanity check

| case | cluster_id | SCOTUS in / out (merged) | cited by all courts |
|---|---|---|---|
| Bell Atlantic v. Twombly, 550 U.S. 544 | 145730 | 21 / 52 | 155,785 |
| Ashcroft v. Iqbal, 556 U.S. 662 | 145875 | 30 / 33 | 159,004 |
| Celotex v. Catrett, 477 U.S. 317 | 111722 | 20 / 11 | 122,464 |
| Anderson v. Liberty Lobby, 477 U.S. 242 | 111719 | 41 / 27 | 138,555 |
| Chevron, 467 U.S. 837 | 111221 | 263 / 43 | 20,727 |
| Erie v. Tompkins, 304 U.S. 64 | 103012 | 223 / 53 | 18,685 |
| Marbury v. Madison, 5 U.S. 137 | 84759 | 284 / 0 | 6,055 |
| Brown v. Board, 347 U.S. 483 | 105221 | 191 / 15 | 3,795 |

All plausible: the civil-procedure workhorses are cited constantly by lower courts but only a few dozen times
by the Court itself; the constitutional landmarks are the reverse.

### Duplicate clusters (the `merge` stage)

CourtListener holds thousands of SCOTUS cases twice (an old import plus the Harvard/CAP import, or a slip
opinion plus the bound-volume version): 5,273 U.S. cites are shared by more than one active cluster, e.g.
Gideon (372 U.S. 335) is clusters 8954562 (in-degree 329) and 106545 (88); Loper Bright is 9986254 and
10600041. A page can also hold several distinct orders (464 U.S. 928 is both *Brown v. Herald* and
*Unterthiner v. Desert Hospital*), so merging on the cite alone is wrong. The `merge` stage folds two active
clusters only when they share the U.S. cite, the filing date (or year) and at least half of the shorter
case name's non-stopword tokens; the member with more SCOTUS edges becomes canonical. That folds 3,235
clusters (2,859 groups) and removes 1,283 edges that became self-loops. Cases whose two copies carry
different names (e.g. *The Minnesota Rate Cases* vs *Simpson v. Shepard*) stay separate; a hand list could
extend `scotus_cluster_merge_map.csv` if they matter.

Outputs: `scotus_nodes_merged.csv` (adds `merged_cluster_ids`; degree columns summed across the group),
`scotus_edges_merged.csv`, `scotus_cluster_merge_map.csv` (`cluster_id -> canonical_cluster_id`).

### Other things to know before using the graph

- `depth` on an edge is how many times the citing opinion text cites the cited one (summed over the opinions
  in the cluster); `opinion_pairs` is how many opinion-level rows collapsed into the edge (e.g. majority and
  dissent both citing the same case). Edge direction is citing -> cited, so in time it always points backwards.
- `us_cite` is the first `U.S.` cite CL has for the cluster. 1,750 active clusters have none (mostly 2020s
  slip opinions that have not yet been assigned U.S. Reports pages, and a few old cases with only `Wall.`/`How.`
  style cites); `all_cites` lists everything CL has.
- Coverage of recent years is thin on the order side (2020s: 3.7k clusters vs 88k for the 2010s) because the
  cert-denial lists come from the Harvard scans, which stop around 2019. Merits opinions are complete.
- The citation extraction is CL's eyecite; it misses "id." chains and some short-form cites, and the
  `citation_count` column in the clusters dump is CL's own aggregate of the same data.

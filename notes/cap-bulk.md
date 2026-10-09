# CAP static bulk data: SCOTUS citation graph

Second, independent source for the cite-race graph (the first is CourtListener bulk).
Everything here comes from https://static.case.law/ (Harvard Library Innovation Lab's
Caselaw Access Project, "CAP"). No API calls; plain `curl` of static files. CourtListener
was not used anywhere in this pipeline.

## Headline: coverage ends June 2014 (U.S. Reports) / August 2020 (S. Ct. extension)

**CAP's U.S. Reports data stops at volume 572 U.S., last decision 2014-06-03.** The
reporter metadata says `"start_year": 1754, "end_year": 2014`. There is no 573+ U.S.
anywhere on static.case.law, and nothing has been added since the 2024-03 open release
(every zip is `Last-Modified: 04 Mar 2024`; `last_updated` inside the JSON is 2024-02-27).
Free Law Project has not extended CAP's static files; FLP's newer SCOTUS coverage lives
only in CourtListener.

CAP does, however, carry a separate `s-ct` (West's Supreme Court Reporter) reporter with
**volumes 134-140 S. Ct. only** (decisions 2013-07-16 to 2020-08-25). I downloaded those
too and folded them in: anything already present in U.S. Reports is dropped (matched on the
shared L. Ed. 2d parallel cite, else on decision date + case name), which leaves 602
real opinions from mid-2014 through August 2020 that U.S. Reports does not have. So the
combined graph covers **1791 to 2020-08-25**, but with a seam: cases after June 2014 have
only an S. Ct. (and usually L. Ed. 2d) cite, no "NNN U.S. NNN" (3 exceptions in 135 S. Ct.,
e.g. Obergefell 576 U.S. 644), and nothing after August 2020 exists at all.
Anything the game wants from the 2020-21 term onward must come from CourtListener.

## Layout of static.case.law

- `https://static.case.law/` : one folder per reporter slug (`us`, `s-ct`, `f3d`, ...), plus
  `ReportersMetadata.json`, `VolumesMetadata.json`, `JurisdictionsMetadata.json`.
- `https://static.case.law/us/` : per-volume rows, each with `N/` (browsable directory),
  `N.zip`, `N.pdf`, `N.tar`, `N.tar.csv`, `N.tar.sha256`, plus `ReporterMetadata.json` and
  `VolumesMetadata.json` for the reporter. 572 volumes, numbered 1-572 with no gaps.
- `N.zip` (what we use; 1-5 MB each) contains:
  - `metadata/VolumeMetadata.json`
  - `metadata/CasesMetadata.json` : array of case records **including `cites_to`** (so the
    per-case files are not needed for the graph)
  - `json/PPPP-NN.json` : one per case (`0544-01.json` = first case starting on page 544);
    same fields as CasesMetadata plus `casebody` (head_matter, opinions[] with type/author/
    text, judges, attorneys)
  - `html/PPPP-NN.html` : rendered case
- `N.tar` is the page scans (ALTO XML + TIFF/JPG), hundreds of MB per volume; not needed.
- `N/` directory view additionally lists `case-pdfs/`.
- The documentation site (case.law/docs) is JS-rendered and not fetchable by plain HTTP;
  everything above was established by inspecting the files directly.

## Case record schema (CasesMetadata.json / json/*.json)

```
id                 CAP case id (int), e.g. 3556136 = Bell Atlantic v. Twombly
name, name_abbreviation, decision_date ("YYYY-MM-DD", sometimes "YYYY-MM" or "YYYY" for 18th c.)
docket_number, first_page, last_page, first_page_order, last_page_order, file_name
citations[]        {type: official|parallel|vendor, cite}   e.g. "550 U.S. 544", "127 S. Ct. 1955",
                   "167 L. Ed. 2d 929", "2007 U.S. LEXIS 5901", "SCDB 2006-045"; early volumes
                   carry the nominative cite ("1 Dall. 1", "5 Wall. 7") as a parallel
court              {id: 9009, name: "Supreme Court of the United States", name_abbreviation: "U.S."}
jurisdiction       {id: 39, name: "U.S."}
analysis           {word_count, char_count, cardinality, ocr_confidence, pagerank{raw,percentile}, sha256, simhash}
last_updated, provenance{date_added, source, batch}
cites_to[]         one entry per distinct cited authority:
   cite            the cite string as printed, e.g. "513 U. S. 251" (note "U. S." with a space)
   category        reporters:federal | reporters:scotus_early | reporters:state | reporters:state_regional |
                   laws:leg_statute | laws:leg_session | laws:admin_compilation | journals:journal | ...
   reporter        normalised reporter name: "U.S.", "S. Ct.", "F.3d", "Wall.", "U.S.C." ...
   case_ids[]      CAP ids of the cited case(s) when CAP resolved the cite (absent otherwise)
   case_paths[]    e.g. "/us/513/0251-01" (same information as case_ids)
   weight          number of times cited in the opinion (absent when 1)
   year            year of the cited authority when known
   pin_cites[]     {page, parenthetical?}
   opinion_index   which opinion in casebody.opinions the cite appears in (0 = majority)
```

Weights: `weight` is absent for single mentions, so the build treats missing as 1.

## What was downloaded

`scripts/cap_download.sh` : sequential `curl -C -` with retries and a 0.3 s pause, verifying
each zip with `zipfile.testzip()` before writing a `.ok` marker (re-runs skip finished files).

| set | files | size |
|---|---|---|
| `data/cap/raw/us/` 1.zip ... 572.zip + 2 metadata JSON | 572 zips | 1.2 GB |
| `data/cap/raw/s-ct/` 134.zip ... 140.zip + 2 metadata JSON | 7 zips | 101 MB |
| total | 579 zips | 1.3 GB, ~17 min |

## Build (`scripts/cap_build_graph.py`)

Reads only `metadata/CasesMetadata.json` from each zip (run with `python -I`, paths passed
as arguments; the raw directory is never on `sys.path`).

Nodes:
1. All cases from `us` volumes with `court.name_abbreviation == "U.S."`. The early
   nominative volumes (1-4 Dall. etc.) also contain Pennsylvania state cases; 1,539 such
   non-SCOTUS records were dropped.
2. Cases from `s-ct` volumes not already present (6,790 duplicates folded into their
   U.S. Reports node; the mapping is in `scotus_alias_sct_to_us.csv`). 46,422 added, of
   which only 602 are real opinions; the rest are orders.
3. `is_order_like = word_count < 300`. U.S. Reports volumes include every cert denial and
   summary order as its own "case" (e.g. 572 U.S. 1001 holds dozens), and 92% of all
   records are such orders. Many orders *do* carry a cite (to the lower-court decision), so
   the flag is length-based, not cite-based. Stats exclude them; the CSV keeps them.

Edges (citing -> cited, one row per pair, weight summed over parallel-cite entries):
- Path A `case_ids`: CAP's own resolution. 400,201 cite entries -> 346,298 pairs resolved by
  this path only.
- Path B `cite_string`: when `case_ids` is empty, parse "NNN Reporter PPP", normalise the
  reporter ("U. S.", "Howard", "Dallas", "Wh." -> us/how/dall/wheat ...) and look it up
  against every node's official + parallel + nominative cites; only unique hits count
  (44 ambiguous cites discarded). 1,389 entries -> 1,009 pairs only reachable this way.
- Path C `page_range`: cite string falls strictly inside a node's [first_page, last_page]
  in the same volume/reporter (a pin cite or a cite to a non-first page). 17,526 entries
  -> 12,312 pairs only reachable this way. Spot checks were all correct, but this path is
  the least certain; filter `via == "page_range"` out of `scotus_edges.csv` if you want
  only CAP-asserted links.
- Total: **363,443 directed edges** between 374,878 nodes (314,443 edges among the 29,234
  non-order nodes).

`scotus_out_cites_all.csv` keeps all 755,433 `cites_to` entries from every SCOTUS record,
with reporter/category/case_ids/resolution. Of the 653,968 entries that point at a case
reporter, 419,117 resolve to a SCOTUS node; the rest are cites to lower federal courts
(F.2d 46k, F. 27k, F. Supp. 10k, F.3d 10k), state courts, and 2,949 "U.S." cites CAP
could not pin down (mostly cites to orders at ambiguous pages like "547 U. S. 1205").

### Output files (`data/cap/`)

| file | rows | columns |
|---|---|---|
| `scotus_nodes.csv` | 374,878 | cap_case_id, case_name, us_cite, decision_date, year, sct_cite, led_cite, other_cites (pipe-joined: nominative, LEXIS, SCDB, U.S.L.W.), official_cite, case_name_full, docket_number, source_reporter (us / s-ct), source_volume, first_page, last_page, word_count, cap_pagerank_pct, n_cites_to, is_order_like, court |
| `scotus_edges.csv` | 363,443 | citing_cap_id, cited_cap_id, weight, via (case_ids / cite_string / page_range, "+"-joined) |
| `scotus_out_cites_all.csv` | 755,433 | citing_cap_id, cite, reporter, category, weight, year, case_ids, resolved_cap_id, via, opinion_index |
| `scotus_alias_sct_to_us.csv` | 6,790 | sct_cap_id, us_cap_id |
| `build_summary.json` | | all counters above |
| `graph_stats.md`, `graph_stats_us_only.md` | | full stats output |

## Statistics (`scripts/cap_graph_stats.py`, order-like nodes excluded, seed 1)

Combined graph (U.S. Reports + S. Ct. 2014-2020): 29,234 opinion nodes, 314,443 edges,
1,279 isolated nodes; largest weakly connected component 27,922 (95.5%). U.S.-only
(`--us-only`): 28,632 nodes, 303,829 edges, LCC 27,330 (95.5%).

Nodes per decade (combined): 1790s 43, 1800s 171, 1810s 346, 1820s 362, 1830s 445,
1840s 343, 1850s 859, 1860s 893, 1870s 1,946, 1880s 2,388, 1890s 2,410, 1900s 1,911,
1910s 2,336, 1920s 1,956, 1930s 1,603, 1940s 1,452, 1950s 1,049, 1960s 1,395, 1970s 1,999,
1980s 2,159, 1990s 1,262, 2000s 894, 2010s 928, 2020s 84 (Jan-Aug 2020 only).

Degree (combined): mean in = mean out = 10.76; median in 5, median out 6; max in 468,
max out 199.

| in-degree | nodes | share | | out-degree | nodes | share |
|---|---|---|---|---|---|---|
| 0 | 3,790 | 13.0% | | 0 | 4,322 | 14.8% |
| 1 | 2,858 | 9.8% | | 1 | 2,854 | 9.8% |
| 2-5 | 8,088 | 27.7% | | 2-5 | 7,258 | 24.8% |
| 6-10 | 5,452 | 18.6% | | 6-10 | 5,027 | 17.2% |
| 11-25 | 6,016 | 20.6% | | 11-25 | 6,452 | 22.1% |
| 26-50 | 2,169 | 7.4% | | 26-50 | 2,603 | 8.9% |
| 51-100 | 713 | 2.4% | | 51-100 | 638 | 2.2% |
| 101-250 | 140 | 0.5% | | 101-250 | 80 | 0.3% |
| 251-500 | 8 | 0.0% | | 251-500 | 0 | 0.0% |

Top 20 most-cited within the SCOTUS graph (full top 40 in `graph_stats.md`):

| rank | case | cite | year | in | out |
|---|---|---|---|---|---|
| 1 | M'Culloch v. Maryland | 17 U.S. 316 | 1819 | 468 | 1 |
| 2 | Gibbons v. Ogden | 22 U.S. 1 | 1824 | 398 | 6 |
| 3 | Gregg v. Georgia | 428 U.S. 153 | 1976 | 310 | 23 |
| 4 | Marbury v. Madison | 5 U.S. 137 | 1803 | 308 | 0 |
| 5 | Yick Wo v. Hopkins | 118 U.S. 356 | 1886 | 301 | 14 |
| 6 | Boyd v. United States | 116 U.S. 616 | 1886 | 289 | 0 |
| 7 | Miranda v. Arizona | 384 U.S. 436 | 1966 | 267 | 82 |
| 8 | Osborn v. Bank of the United States | 22 U.S. 738 | 1824 | 266 | 7 |
| 9 | Cohens v. Virginia | 19 U.S. 264 | 1821 | 236 | 16 |
| 10 | Chevron v. NRDC | 467 U.S. 837 | 1984 | 228 | 43 |
| 11 | Ex parte Young | 209 U.S. 123 | 1908 | 215 | 101 |
| 12 | Slaughter-House Cases | 83 U.S. 36 | 1872 | 214 | 2 |
| 13 | Brown v. Maryland | 25 U.S. 419 | 1827 | 210 | 7 |
| 14 | Ashwander v. TVA | 297 U.S. 288 | 1936 | 210 | 106 |
| 15 | Fletcher v. Peck | 10 U.S. 87 | 1810 | 207 | 1 |
| 16 | Erie Railroad v. Tompkins | 304 U.S. 64 | 1938 | 205 | 53 |
| 17 | Cantwell v. Connecticut | 310 U.S. 296 | 1940 | 201 | 9 |
| 18 | Gideon v. Wainwright | 372 U.S. 335 | 1963 | 201 | 51 |
| 19 | Munn v. Illinois | 94 U.S. 113 | 1876 | 193 | 27 |
| 20 | Chicago, B. & Q. R. Co. v. Chicago | 166 U.S. 226 | 1897 | 191 | 33 |

The ranking is skewed toward 19th-century constitutional cases because the graph counts
only SCOTUS-citing-SCOTUS and 19th-century opinions cited each other densely; a modern
case like Chevron has had only 36 years to accumulate in-links, and nothing after
August 2020 counts.

Sanity checks (combined graph):

| case | cite | found | decided | in | out |
|---|---|---|---|---|---|
| Bell Atlantic v. Twombly | 550 U.S. 544 | yes | 2007-05-21 | 13 | 49 |
| Ashcroft v. Iqbal | 556 U.S. 662 | yes | 2009-05-18 | 19 | 32 |
| Celotex v. Catrett | 477 U.S. 317 | yes | 1986-06-25 | 14 | 9 |
| Anderson v. Liberty Lobby | 477 U.S. 242 | yes | 1986-06-25 | 36 | 24 |
| Chevron v. NRDC | 467 U.S. 837 | yes | 1984-06-25 | 228 | 43 |
| Erie v. Tompkins | 304 U.S. 64 | yes | 1938-04-25 | 205 | 53 |
| Marbury v. Madison | 5 U.S. 137 | yes | 1803-02 | 308 | 0 |
| Brown v. Board of Education | 347 U.S. 483 | yes | 1954-05-17 | 173 | 15 |
| Obergefell v. Hodges | 576 U.S. 644 (S. Ct.-volume node, 135 S. Ct. 2584; one of 3 S. Ct. nodes with a U.S. cite) | yes | 2015-06-26 | 13 | 55 |
| Bostock v. Clayton County | 140 S. Ct. 1731 | yes | 2020-06-15 | 0 | 58 |

Twombly's 13 looks low but is real for a SCOTUS-only graph through 2020: a full-text scan
of the opinions in 550-572 U.S. and 134-140 S. Ct. finds "Twombly" in only 15 later
opinions, and `cites_to` links 13 of them (87% recall on that spot check). Celotex 14 and
Anderson 36 are likewise SCOTUS-internal counts, not the thousands of lower-court cites.

Shortest paths (edges treated as undirected; 2,000 random pairs sampled inside the largest
component; BFS via scipy):

| path length | full graph | top-20 hubs removed | top-100 hubs removed |
|---|---|---|---|
| 1 | 0 | 0 | 2 (0.1%) |
| 2 | 54 (2.7%) | 47 (2.4%) | 31 (1.6%) |
| 3 | 529 (26.4%) | 471 (23.6%) | 431 (21.6%) |
| 4 | 969 (48.5%) | 1,031 (51.5%) | 1,035 (51.8%) |
| 5 | 384 (19.2%) | 392 (19.6%) | 446 (22.3%) |
| 6 | 63 (3.1%) | 56 (2.8%) | 51 (2.5%) |
| 7 | 0 | 3 (0.1%) | 4 (0.2%) |
| 8 | 1 (0.1%) | 0 | 0 |
| mean | 3.94 | 3.97 | 4.03 |
| LCC size | 27,922 of 29,234 (95.5%) | 27,884 of 27,917 (99.9%) | 27,773 of 27,808 (99.9%) |

Hub removal (top 20 by undirected degree = degree >= 247; top 100 = degree >= 178) barely
changes the picture: the graph stays one giant component and the typical random pair is
still 4 hops apart. Good news for a citation-race game: there is no small set of
"cheat" hubs whose removal breaks the puzzle, and 97% of pairs are solvable in 5 or fewer
hops even with the 100 biggest hubs banned. The U.S.-only graph gives the same
distribution (mean 3.94 / 4.00 / 4.01).

## Pitfalls

1. **Coverage stops at 572 U.S. (June 2014)**; the S. Ct. extension stops at 140 S. Ct.
   (August 2020). Nothing newer exists on static.case.law and nothing has been updated
   since the March 2024 release. Treat this as a frozen historical snapshot.
2. **92% of "cases" are orders.** Filter on `is_order_like == 0` (word_count >= 300) or on
   `word_count` directly. Nothing about the record type distinguishes them otherwise.
3. **Early volumes (1-4 Dall.) contain Pennsylvania cases**; filter on
   `court.name_abbreviation == "U.S."`. 1,539 dropped.
4. **S. Ct. 2014-2020 nodes have no U.S. cite** (599 of 602 opinions). Match on S. Ct. or
   L. Ed. 2d cite (548 of 602 have one), or by name/date, when merging with CourtListener.
5. **Cite strings are OCR'd**: "U. S." with a space, "Howard," "Cranch," "Dall. Rep.",
   "Wh." (which CAP labels Wharton but SCOTUS means Wheaton), stray commas and quotes.
   `rep_key()` in the build script normalises them; CAP's own `case_ids` cover 95% of
   resolved cites so this only matters at the margins.
6. **Weight is absent when 1.** Missing `weight` means one mention.
7. **Duplicate entries**: the same case is sometimes cited by both its U.S. and S. Ct. cite
   in one opinion; the build sums weights into one edge per pair.
8. Decision dates in the 18th century are sometimes "YYYY" or "YYYY-MM"; `year` is the
   first four characters.
9. The raw downloads are treated as untrusted: scripts never `cd` into `data/cap/raw`,
   only `json.loads` from zip members, and run with `python -I`.

## Re-running

```bash
cd "C:/Users/Rebecca Fordon/Projects/cite-race"
bash scripts/cap_download.sh                                   # ~17 min, 1.3 GB, resumable
python -I scripts/cap_build_graph.py --raw data/cap/raw --out data/cap     # ~1 min
python -I scripts/cap_build_graph.py --raw data/cap/raw --out data/cap --no-sct   # U.S. Reports only
python -I scripts/cap_graph_stats.py --data data/cap --pairs 2000          # writes graph_stats.md
python -I scripts/cap_graph_stats.py --data data/cap --pairs 2000 --us-only
```

Requires networkx, numpy, scipy (all already installed for python 3.11).

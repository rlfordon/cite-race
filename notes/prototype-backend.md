# Prototype backend (scripts/serve.py)

Implements `notes/prototype-api.md` (v0, 2026-10-09, including the `mode` parameter). Stdlib only.

## Run

```
cd "C:/Users/Rebecca Fordon/Projects/cite-race"
python -I scripts/serve.py            # http://127.0.0.1:8765/   (--port N, --rebuild to redo the cache)
```

Startup: **~21 s on a cold run** (builds the cache), **0.3 s warm** (loads the pickle). The server serves
`app/index.html` at `/`, any file under `app/` by path (no traversal outside `app/`; 503 if `index.html`
is missing yet), and the JSON API under `/api/`. Extra: `/api/stats` (index counts), and every `/api/case`
response carries a `text_stats` object (cites_to counts, links made) for debugging.

## Files

| file | role |
|---|---|
| `scripts/serve.py` | ThreadingHTTPServer, routes, BFS, puzzle, opponent |
| `scripts/prototype_index.py` | builds / loads the cache; `python -I scripts/prototype_index.py --force` rebuilds it alone |
| `scripts/cap_text.py` | CAP HTML -> opinion body with `<a class="cite" data-id>` links |
| `scripts/exclusions.py` | boilerplate hub ids (Detroit Timber 96405, Martin v. D.C. Ct. App. 112790, Brown v. Herald 111075, Gregg v. Georgia 109532) |
| `data/prototype/index.pickle` | the cache (9.5 MB): nodes, out/in adjacency, text index, CAP->CL map |
| `data/prototype/cap_text_index.csv` | human-readable copy of the text index: `cl_id, cap_id, zip_path, member_path, word_count, cap_name` |

The raw zips under `data/cap/raw` are never on `sys.path`; members are only `decode()`d / `json.loads()`'d.
`serve.py` adds its own `scripts/` directory to `sys.path` (needed under `-I`) to import the sibling modules.

## How the graph is built (prototype_index.py)

1. `scotus_edges_merged.csv` is read; edges touching an excluded hub are dropped, and so are **274 edges that
   point forward in time** (cited year > citing year; CL resolution noise, e.g. McGourkey 1892 -> Jones v. Bock
   2007). Same-year edges are kept.
2. **Duplicate clusters are folded.** CL still holds some cases twice (slip opinion + bound volume, or two imports
   with different dates; the CL `merge` stage only folded pairs sharing cite and date) and one copy cites the other,
   which produced paths like "Montana v. United States (1981) -> Montana v. United States (1981)". When an edge joins
   two nodes of the same year that share the U.S. cite or whose case-name tokens have Jaccard overlap >= 0.6, they
   are folded into the better-connected one (union-find; in-degree counts summed, cites pooled so CAP links to
   either cite resolve): **2,385 clusters folded into 2,290, 2,482 self-edges dropped**. Then any remaining
   same-year edge whose names share >= half their non-generic tokens (companion orders, rehearing denials) is
   dropped: **821 edges**. `index["folded"]` maps the 1,317 folded ids inside the giant component to their canonical.
3. The giant component of the undirected graph is taken: **36,506 nodes, 295,785 directed edges**
   (the merged graph had 39,497 before the hubs went; removing Gregg alone detaches ~1,200 cert-denial dissents).
4. Nodes come from `scotus_nodes_merged.csv`: `cited_all = indeg_all_courts`, `cited_scotus = indeg_scotus`,
   `cite = us_cite` (first other cite if none).
5. CAP join. `data/cap/scotus_nodes.csv` plus a scan of `metadata/CasesMetadata.json` in all 579 zips (13 s) gives
   each CAP id its `html/<page>-<n>.html` member. Two maps:
   - **CL -> CAP record (text)**: by `us_cite`; S. Ct.-era CL nodes (no U.S. cite in CAP) by the S. Ct. / L. Ed. 2d
     cite in CL's `all_cites`. When several CAP records share the page (orders), the one whose name shares >= half
     its tokens with the CL name wins; with no name match, the single real opinion on the page is taken only if
     its year matches; otherwise no text. Result: **34,825 of 36,506 nodes have text; 27,333 are real opinions**
     (CAP word_count >= 300) and form the puzzle pool.
   - **CAP id -> CL id (link resolution)**: by `us_cite`, else S. Ct. / L. Ed. cite, choosing among duplicate CL
     clusters by (name match, graph degree, year). 58,583 CAP records resolve to a graph node; the S. Ct. duplicate
     aliases are folded in.

## Opinion text (cap_text.py)

Read lazily per request from the zip (`html/...html` for the body, the matching `json/...json` for `cites_to`;
15-30 ms per case, ~180 ms under 10 parallel requests). Processing:

- drop `data-blocks` attributes, `<p class="attorneys">` and `<img>`; page labels become `<span class="page-label">`.
  Everything else (head-matter caption, dates, syllabus/headnotes where CAP has them, `<article class="opinion">`
  per opinion in order, `<aside class="footnote">`, `<em>`, blockquotes) is kept as is.
- CAP already wraps every citation it recognises as `<a class="citation" data-case-ids=...>`. Those anchors are
  rewritten: if the CAP ids resolve to exactly one graph node (and not the case itself) ->
  `<a class="cite" data-id="<cl id>">...</a>`; otherwise unwrapped to plain text. Short-form cites CAP tagged
  (`Id.`, `supra`, `at 347`) become links to the same node.
- A second pass scans text nodes outside any `<a>` for `cites_to` strings CAP did not wrap (rare: 0 in the cases
  checked).
- A preceding case name of the form `Xxx v. Yyy, ` / `Ex parte Xxx, ` is pulled into the link (em tags tolerated,
  signal words like "See", "Cf.", "In", "First." stripped, sentence boundaries respected via an abbreviation rule;
  the link is only extended when the `<em>` nesting stays balanced).

Erie (304 U.S. 64, cluster 103012): CAP lists **93 `cites_to` entries, 73 of them to cases with CAP ids, 54 of
which resolve to a node of the game graph**; the body gets **82 links covering 53 distinct cases** (CAP had wrapped
126 anchors: journals, statutes, short-form cites included). The merged edge table has 53 out-edges for Erie:
52 overlap with the linked set, 1 edge-neighbour is not linked in the text and 1 linked case is not in the edges.
`cites` always comes from the edge table, so both still show in the list.

## Endpoints

- `/api/puzzle?seed=N&mode=any|back|forward`: `random.Random(seed)` (seed + mode for the directed modes) picks a
  start from the sorted eligible pool, BFS to depth 5 under the mode, picks a target among eligible nodes at
  distance 3..5; retries with another start if none. `par = shortest + 2`. `shortest` is measured under the mode.
- `/api/case/<id>`: node + `html` + `cites` (edge-table out-neighbours, by year) + `cited_by` (in-neighbours, by
  `cited_all` desc) + `cited_by_total` (= len, hubs already gone). 404 for ids outside the game graph (unknown,
  isolated, or an excluded hub). Nodes without text return `html: ""` and a `note`.
- `/api/path?from&to&mode`: BFS; `{"length": null}` when unreachable (e.g. `mode=back` against time).
- `/api/opponent?puzzle&at&target&visited&mode`: `Random(f"{seed}:{at}:{mode}")`; candidates = neighbours under
  the mode minus `visited`; with p=0.6 a neighbour one hop closer to the target (BFS distance cached per
  target/mode), else a random one of the 10 most-cited (`cited_all`). `move: null` when nothing is left.

## Path lengths (1,000 random pairs of eligible nodes, seed 1, BFS capped at 9)

| hops | any | back (start -> target along citations) | forward (along cited-by) |
|---|---|---|---|
| 2 | 2.1% | 0.4% | 0.6% |
| 3 | 20.3% | 3.6% | 2.9% |
| 4 | 45.5% | 8.6% | 9.7% |
| 5 | 25.0% | 9.3% | 10.9% |
| 6 | 6.3% | 5.0% | 5.3% |
| 7-9 | 0.8% | 3.2% | 3.2% |
| unreachable | 0 | 69.9% | 67.4% |

Random pairs are mostly unreachable in a directed mode (half the pairs point the wrong way in time, and the DAG is
sparse), but puzzle generation does not need random pairs: of 300 sampled eligible starts, 300 (any), 237 (back)
and 264 (forward) have an eligible target 3-5 hops away, so the retry loop finds a puzzle quickly in every mode.

## Known gaps

- Post-2020 (and the 2014-2020 cases CAP's S. Ct. volumes lack) have `has_text: false`; ~1,750 giant-component
  nodes, mostly 2020s slip opinions and a few misfiled Court of Claims clusters.
- Case-name extension is heuristic: names with lowercase words other than the usual connectors (`of`, `the`,
  `and`, `de`, `for`) stop early ("B. & Q. R. Co. v. Chicago" for "Chicago, B. & Q. R. Co."), and a capitalised
  word before the name that is not in the signal list is occasionally swallowed.
- Pin cites ("at 347") and `Id.` that CAP tagged are separate links to the same case; the client may want to style
  them lower-key.
- CAP's `cites_to` resolution misses some cites the CL edge table has and vice versa (1 each way in Erie), so a
  case can be clickable in the sidebar list but plain in the text, or the reverse.
- Duplicate CL clusters are only folded when one copy cites the other (step 2 above). Copies that share a cite but
  have no edge between them (different years, ~2,000 U.S. cites) are both still in the graph; links go to the
  better-connected copy, so a small share of in-links sit on the other copy.
- Puzzle starts are not checked for out-degree in `any` mode: a start may have no citations in its text (e.g. an
  1880 one-pager) and only `cited_by` moves.
- The opponent is the specified stand-in, not Jev.

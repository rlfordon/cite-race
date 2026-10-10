# Prototype API contract (v0, 2026-10-09)

Local server: `python -I scripts/serve.py` on http://127.0.0.1:8765. Serves `app/index.html` at `/` and JSON under `/api/`. Stdlib `http.server` is fine; no auth; CORS not needed (same origin).

## Node shape
```
{ "id": 304064, "name": "Erie R. Co. v. Tompkins", "cite": "304 U.S. 64", "year": 1938,
  "date": "1938-04-25", "cited_all": 18685, "cited_scotus": 223, "has_text": true }
```
`id` is the CourtListener merged cluster id. `cited_all` is all-court in-degree (for sorting); `cited_scotus` is SCOTUS in-degree.

## Endpoints
- `GET /api/puzzle?seed=<int>&mode=<any|back|forward>` → `{ "seed", "mode", "start": node, "target": node, "shortest": 4, "par": 6 }`
  `mode=any` (default): undirected path, either direction allowed each hop. `mode=back`: only citations in the opinion (edges citing→cited), so the target is older than the start and the path is directed start→target in the edge table. `mode=forward`: only the cited-by list, target newer; equivalently a directed path target→start. Pairs for `back`/`forward` must have a directed path of length 3 to 5.
  Picks a pair from the giant component where both have text, both are real opinions (not orders, word count >= 300), neither is boilerplate, and the undirected shortest path is 3 to 5. `par = shortest + 2`. Deterministic for a seed.
- `GET /api/case/<id>` → `{ ...node, "html": "<opinion body>", "cites": [node...], "cited_by": [node...], "cited_by_total": n }`
  `html` is the opinion text with each resolvable citation wrapped as `<a class="cite" data-id="<cluster id>">Swift v. Tyson, 16 Pet. 1</a>` (include the case name before the cite in the link when it immediately precedes it). Unresolvable cites stay plain text. Strip scripts/styles; keep paragraphs, headings, small caps spans, footnotes if easy.
  `cites` = backward neighbours (cases this one cites) from the merged SCOTUS edges, each a node, sorted by year.
  `cited_by` = forward neighbours (SCOTUS cases citing this one), sorted by `cited_all` desc, all of them (max is a few hundred). Boilerplate hubs excluded. Client filters by year and word.
- `GET /api/path?from=<id>&to=<id>&mode=<any|back|forward>` → `{ "length": 4, "path": [node...] }` BFS respecting the mode (undirected for `any`, directed for the others), or `{ "length": null }`.
- `GET /api/opponent?puzzle=<seed>&at=<id>&target=<id>&visited=<id,id,...>&mode=<any|back|forward>` → (candidate neighbours restricted by mode) `{ "move": node, "note": "stand-in" }`
  Stand-in for Jev until the typed-judgment version is wired: if the target is an unvisited neighbour, take it; otherwise with probability 0.6 choose the neighbour (either direction) that is one step closer to the target by BFS, otherwise choose a random neighbour among the 10 most-cited. Never revisit `visited`. Deterministic per (seed, at).

## Text source
CAP HTML from `data/cap/raw/us/<vol>.zip` → `html/<path>.html`, joined to CourtListener nodes on `us_cite` (see `data/cap/scotus_nodes.csv`, `data/cap/scotus_alias_sct_to_us.csv`). Post-2020 cases have no text in the prototype: `has_text: false`, and they are excluded from puzzles but may appear in lists (render them unclickable with a note).

## Exclusions (boilerplate hubs)
Detroit Timber & Lumber (syllabus disclaimer), Martin v. D.C. Court of Appeals and Brown v. Herald (IFP orders), Gregg v. Georgia cert-denial dissents as a hub source. Keep a list in `scripts/exclusions.py` so it can grow.

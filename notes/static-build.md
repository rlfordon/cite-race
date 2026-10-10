# Static build for GitHub Pages (docs/)

The Pages build runs the whole game in the browser: `app/static-api.js` replaces `scripts/serve.py`, the
citation graph ships as `docs/data/graph.json`, and opinion text is fetched per hop from the Caselaw
Access Project archive at static.case.law. The page (`app/index.html`) is unchanged; the copy in `docs/`
only carries `<body data-static="1">`, which the page reads to route its `/api/...` fetches through
`window.StaticApi.call(path)` instead of the network.

## Rebuild

```
cd "C:/Users/Rebecca Fordon/Projects/cite-race"
python -I scripts/build_static.py        # ~3 s; needs data/prototype/index.pickle (python -I scripts/prototype_index.py builds it, ~21 s)
```

Writes `docs/data/graph.json`, `docs/data/starters.json`, `docs/index.html`, `docs/static-api.js`, `docs/.nojekyll`.
Rerun after changing `app/index.html`, `app/static-api.js`, `data/prototype/starters.json` or the index.

`docs/data/jev.json` (Jev's precomputed routes) is built separately by `python scripts/precompute_jev.py`,
which needs `TYPESAFE_API_KEY` in `.env`; see `notes/design-decisions.md`. Rerun it after the graph or
starters change, since routes are keyed by CourtListener cluster ids and the random pool is drawn from the graph.

Smoke test (graph, puzzles, paths, opponent, a live archive fetch and the error codes):

```
(cd docs && python -m http.server 8777)                 # in another shell
node scripts/static_smoke.mjs http://127.0.0.1:8777/    # optional 2nd arg: a dir of ref_<clid>.html files
                                                        # rendered by cap_text.py, compared byte for byte
```

## Sizes (2026-10-09 build)

| file | raw | gzipped |
|---|---|---|
| `docs/data/graph.json` | 7.72 MB | 1.98 MB |
| `docs/data/starters.json` | 15 KB | 3 KB |
| `docs/data/jev.json` | 19 KB | 6 KB |
| `docs/data/notable.json` | 129 KB | 50 KB |
| `docs/index.html` | 36 KB | 11 KB |
| `docs/static-api.js` | 18 KB | 7 KB |

GitHub Pages gzips JSON on the wire, so the first load is about 2 MB; parsing plus building the adjacency
arrays takes ~250 ms. Both JSON files are fetched lazily on the first `StaticApi.call`, relative to the page
URL (`StaticApi.base` overrides that).

## graph.json

Node ids are re-indexed 0..N-1 in ascending CourtListener cluster id. Parallel arrays: `ids` (CL cluster id),
`names`, `cites`, `years`, `dates`, `cited_all`, `cited_scotus`, `has_text` (0/1), `real` (0/1), `text`
(null or `[reporter, vol, member]`), `cap_ids` (CAP case ids resolving to the node, for the text links), and
`edges`, a flat `[citing, cited, ...]` array in new indexes sorted by (citing, cited); 36,506 nodes, 295,785
edges, 34,825 with text, 27,333 puzzle-eligible. `meta` records the build time and counts. The boilerplate
hubs (`scripts/exclusions.py`) were removed before the pickle was built, so they are absent here too.

`docs/data/starters.json` is `data/prototype/starters.json` with each node's `id` replaced by the new index
and the CL id kept as `cl_id`. The API still hands the page CL ids (it rebuilds node objects from the graph).

## Archive URL

```
https://static.case.law/<reporter>/<vol>/html/<member>.html      reporter: us | s-ct
e.g. https://static.case.law/us/304/html/0064-01.html             Erie R. Co. v. Tompkins
```

`text[i] = ["us", 304, "0064-01"]` gives the three parts. The response is the bare `<section class="casebody">`
with `Access-Control-Allow-Origin: *`, byte-identical to `html/<member>.html` in the local `data/cap/raw` zips
(checked for Erie). The json sidecar (`.../json/<member>.json`, CAP's `cites_to`) is not served (404).

## What differs from the server

- **Puzzle seeds give different pairs.** The rules are the same (eligible = real opinion with text, target 3-5
  hops under the mode, par = shortest + 2, 500 retries) but the PRNG is mulberry32 seeded with an FNV-1a hash
  of the same key Python used (`seed`, or `seed:mode`, and `seed:at:mode` for the opponent), not Python's
  `random.Random`. Seeds are deterministic within the static build, just not across the two backends. Starter
  pairs (`pair=A-B`) and paths are identical: BFS visits neighbours in ascending CL id, as the server does.
- **No cites_to pass.** `cap_text.py` has a second pass that links `cites_to` strings CAP did not wrap, using
  the json sidecar from the zip. The archive does not serve it, so the static build only rewrites CAP's own
  `<a class="citation">` anchors (pass 1) and pulls the preceding case name into the link (pass 3). Pass 2
  made 0 links in every case checked, and the JS output is byte-identical to `cap_text.render(raw, [], ...)`
  for Erie, Plessy, Grutter and Jennings v. Stephens (135 S. Ct.).
- **Text availability is the same as the prototype**, not better: `has_text` comes from the index, so
  post-2020 opinions and the 2014-2020 cases CAP's S. Ct. volumes lack return `html: ""`, `has_text: false`
  and a `note`. The archive is only consulted for nodes the index already matched.
- **Opinion text needs the network**: each hop is one cross-origin GET to static.case.law (50-200 KB,
  ~200 ms); fetched cases are cached in memory for the session. If the archive is down the page shows
  "Could not load that case".
- `/api/case` responses carry `text_stats` as before, minus the cites_to counters. `/api/stats` returns the
  `meta` block plus `eligible` and `cap_to_cl`.
- Errors are thrown as `StaticApi.ApiError` with a `.status` (400/404/500/502) and the server's message,
  instead of an HTTP status; the page's `api()` helper treats a rejected promise the same way as `!r.ok`.

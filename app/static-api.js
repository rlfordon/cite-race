/* Static stand-in for scripts/serve.py, for the GitHub Pages build.
 *
 * window.StaticApi.call('/api/puzzle?seed=1&mode=any') returns a Promise of the same JSON the
 * Python server would send (notes/prototype-api.md). The graph comes from data/graph.json
 * (built by scripts/build_static.py, node ids re-indexed 0..N-1); node objects handed to the
 * page carry the CourtListener cluster id as `id`, so the page is unchanged. Opinion text is
 * fetched per case from the Caselaw Access Project archive (static.case.law, open CORS) and
 * linkified here the way scripts/cap_text.py does.
 *
 * Plain script, no bundler. Also usable under node for tests: provide window, document
 * (body.dataset.static, baseURI) and fetch; nothing touches the DOM.
 */
(function () {
  'use strict';
  const MODES = ['any', 'back', 'forward'];
  const ARCHIVE = 'https://static.case.law';

  // ---------------------------------------------------------------- seeded randomness
  function hash32(str) { // FNV-1a over UTF-16 code units
    let h = 0x811c9dc5;
    for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 0x01000193); }
    return h >>> 0;
  }
  function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const rngFor = key => mulberry32(hash32(String(key)));
  // A one-hop warm-up has nothing to lose a stroke on, so its par is the hop itself.
  const parFor = shortest => (shortest === 1 ? 1 : shortest + 2);
  const choice = (rng, arr) => arr[Math.floor(rng() * arr.length)];

  // ---------------------------------------------------------------- errors
  class ApiError extends Error {
    constructor(status, msg) { super(msg); this.status = status; this.name = 'ApiError'; }
  }

  // ---------------------------------------------------------------- graph
  let G = null;          // parsed graph.json plus CSR adjacency
  let STARTERS = null;   // docs/data/starters.json
  let loading = null;
  const caseCache = new Map();   // cl id -> /api/case response
  const distCache = new Map();   // `${targetIdx}:${mode}` -> Int32Array

  function baseUrl() {
    if (typeof document !== 'undefined' && document.baseURI) return document.baseURI;
    return 'http://localhost/';
  }

  async function fetchJson(rel) {
    const url = new URL(rel, StaticApi.base || baseUrl()).href;
    const r = await fetch(url);
    if (!r.ok) throw new ApiError(r.status, `${rel}: HTTP ${r.status}`);
    return r.json();
  }

  function csr(n, edges, fromOff, toOff) {
    // edges flat [a, b, ...]; rows for node `edges[i+fromOff]` hold `edges[i+toOff]`, in file order
    const m = edges.length / 2;
    const deg = new Int32Array(n + 1);
    for (let i = 0; i < m; i++) deg[edges[2 * i + fromOff] + 1]++;
    for (let i = 0; i < n; i++) deg[i + 1] += deg[i];
    const adj = new Int32Array(m), fill = deg.slice(0, n);
    for (let i = 0; i < m; i++) { const a = edges[2 * i + fromOff]; adj[fill[a]++] = edges[2 * i + toOff]; }
    return { off: deg, adj };
  }

  function mergeSorted(a, b) {
    const out = [];
    let i = 0, j = 0;
    while (i < a.length || j < b.length) {
      if (j >= b.length || (i < a.length && a[i] < b[j])) out.push(a[i++]);
      else if (i >= a.length || b[j] < a[i]) out.push(b[j++]);
      else { out.push(a[i]); i++; j++; }
    }
    return out;
  }

  function prepare(graph) {
    const n = graph.ids.length;
    const out = csr(n, graph.edges, 0, 1);  // rows sorted (edges sorted by citing, cited)
    const inn = csr(n, graph.edges, 1, 0);  // rows sorted (file order is ascending citing)
    const undOff = new Int32Array(n + 1);
    const undRows = new Array(n);
    for (let i = 0; i < n; i++) {
      undRows[i] = mergeSorted(out.adj.subarray(out.off[i], out.off[i + 1]), inn.adj.subarray(inn.off[i], inn.off[i + 1]));
      undOff[i + 1] = undOff[i] + undRows[i].length;
    }
    const undAdj = new Int32Array(undOff[n]);
    for (let i = 0; i < n; i++) undAdj.set(undRows[i], undOff[i]);
    const byCl = new Map();
    for (let i = 0; i < n; i++) byCl.set(graph.ids[i], i);
    const capToIdx = new Map();
    for (let i = 0; i < n; i++) for (const c of graph.cap_ids[i]) capToIdx.set(c, i);
    const eligible = [];
    for (let i = 0; i < n; i++) if (graph.real[i]) eligible.push(i);
    graph.n = n; graph.out = out; graph.in = inn; graph.und = { off: undOff, adj: undAdj };
    graph.byCl = byCl; graph.capToIdx = capToIdx; graph.eligible = eligible;
    return graph;
  }

  function load() {
    if (G && STARTERS) return Promise.resolve();
    if (!loading) {
      loading = Promise.all([fetchJson('data/graph.json'), fetchJson('data/starters.json')]).then(([g, s]) => {
        G = prepare(g); STARTERS = s;
      }).catch(e => { loading = null; throw e; });
    }
    return loading;
  }

  // ---------------------------------------------------------------- graph helpers (indexes)
  const rowOf = (lists, i) => lists.adj.subarray(lists.off[i], lists.off[i + 1]);
  function neighbours(i, mode) { return rowOf(mode === 'back' ? G.out : mode === 'forward' ? G.in : G.und, i); }
  function reverseNeighbours(i, mode) { return rowOf(mode === 'back' ? G.in : mode === 'forward' ? G.out : G.und, i); }

  function nodeObj(i) {
    return { id: G.ids[i], name: G.names[i], cite: G.cites[i], year: G.years[i], date: G.dates[i],
      cited_all: G.cited_all[i], cited_scotus: G.cited_scotus[i], has_text: !!G.has_text[i] };
  }

  function bfsFrom(start, mode, maxDepth) {
    const dist = new Int32Array(G.n).fill(-1), q = new Int32Array(G.n);
    let head = 0, tail = 0;
    dist[start] = 0; q[tail++] = start;
    while (head < tail) {
      const x = q[head++], d = dist[x];
      if (maxDepth != null && d >= maxDepth) continue;
      for (const y of neighbours(x, mode)) if (dist[y] < 0) { dist[y] = d + 1; q[tail++] = y; }
    }
    return dist;
  }

  function distToTarget(target, mode) {
    const key = `${target}:${mode}`;
    let dist = distCache.get(key);
    if (dist) return dist;
    dist = new Int32Array(G.n).fill(-1);
    const q = new Int32Array(G.n);
    let head = 0, tail = 0;
    dist[target] = 0; q[tail++] = target;
    while (head < tail) {
      const x = q[head++], d = dist[x];
      for (const y of reverseNeighbours(x, mode)) if (dist[y] < 0) { dist[y] = d + 1; q[tail++] = y; }
    }
    if (distCache.size >= 64) distCache.delete(distCache.keys().next().value);
    distCache.set(key, dist);
    return dist;
  }

  function shortestPath(a, b, mode) {
    if (a === b) return [a];
    const parent = new Int32Array(G.n).fill(-2), q = new Int32Array(G.n);
    let head = 0, tail = 0;
    parent[a] = -1; q[tail++] = a;
    while (head < tail) {
      const x = q[head++];
      for (const y of neighbours(x, mode)) {
        if (parent[y] !== -2) continue;
        parent[y] = x;
        if (y === b) { const path = [b]; while (parent[path[path.length - 1]] !== -1) path.push(parent[path[path.length - 1]]); return path.reverse(); }
        q[tail++] = y;
      }
    }
    return null;
  }

  // ---------------------------------------------------------------- endpoints
  function apiPuzzle(seed, mode) {
    const rng = rngFor(mode !== 'any' ? `${seed}:${mode}` : seed);
    for (let tries = 0; tries < 500; tries++) {
      const start = choice(rng, G.eligible);
      const dist = bfsFrom(start, mode, 5);
      const cands = [];
      for (let t = 0; t < G.n; t++) if (dist[t] >= 3 && dist[t] <= 5 && G.real[t]) cands.push(t);
      if (!cands.length) continue;
      const target = choice(rng, cands), shortest = dist[target];
      return { seed, mode, start: nodeObj(start), target: nodeObj(target), shortest, par: parFor(shortest) };
    }
    throw new ApiError(500, 'could not find a puzzle for this seed');
  }

  function apiStarters(mode) {
    const out = [];
    for (const s of STARTERS) {
      const d = s.shortest[mode];
      if (d == null) continue;
      const older = nodeObj(s.older.id), newer = nodeObj(s.newer.id);
      const [start, target] = mode === 'back' ? [newer, older] : [older, newer];
      out.push({ group: s.group, theme: s.theme, start, target, shortest: d, par: parFor(d), mode, seed: 0, pair: `${start.id}-${target.id}` });
    }
    return out;
  }

  function apiPairPuzzle(pair, mode) {
    const m = /^(\d+)-(\d+)$/.exec(pair);
    if (!m) throw new ApiError(400, 'pair must be <startid>-<targetid>');
    const a = G.byCl.get(+m[1]), b = G.byCl.get(+m[2]);
    if (a == null || b == null) throw new ApiError(404, 'pair ids are not in the game graph');
    const path = shortestPath(a, b, mode);
    if (!path) throw new ApiError(404, 'no path between that pair in this mode');
    const d = path.length - 1;
    return { seed: 0, mode, pair, start: nodeObj(a), target: nodeObj(b), shortest: d, par: parFor(d) };
  }

  function apiPath(a, b, mode) {
    const path = shortestPath(a, b, mode);
    if (!path) return { length: null, mode };
    return { length: path.length - 1, mode, path: path.map(nodeObj) };
  }

  function apiOpponent(seed, at, target, visited, mode) {
    const rng = rngFor(`${seed}:${G.ids[at]}:${mode}`);
    const cands = Array.from(neighbours(at, mode)).filter(c => c !== at && !visited.has(c)).sort((x, y) => x - y);
    if (!cands.length) return { move: null, note: 'stand-in: no unvisited neighbour' };
    if (cands.includes(target)) return { move: nodeObj(target), note: 'stand-in (target in reach)' };
    const dist = distToTarget(target, mode), here = dist[at];
    const closer = here >= 0 ? cands.filter(c => dist[c] === here - 1) : [];
    const roll = rng();
    let move, how;
    if (roll < 0.6 && closer.length) { move = choice(rng, closer); how = 'closer'; }
    else {
      const top = cands.slice().sort((x, y) => (G.cited_all[y] - G.cited_all[x]) || (x - y)).slice(0, 10);
      move = choice(rng, top); how = 'random-top10';
    }
    return { move: nodeObj(move), note: `stand-in (${how})` };
  }

  async function apiCase(i) {
    const cl = G.ids[i];
    if (caseCache.has(cl)) return caseCache.get(cl);
    let html = '', stats = {};
    const t = G.text[i];
    if (t) {
      const url = `${ARCHIVE}/${t[0]}/${t[1]}/html/${t[2]}.html`;
      const r = await fetch(url);
      if (!r.ok) throw new ApiError(502, `archive ${r.status} for ${url}`);
      [html, stats] = linkify(await r.text(), i);
    }
    const byYear = (x, y) => ((G.years[x] || 0) - (G.years[y] || 0)) || (G.dates[x] < G.dates[y] ? -1 : G.dates[x] > G.dates[y] ? 1 : 0) || (x - y);
    const cites = Array.from(rowOf(G.out, i)).sort(byYear);
    const citedBy = Array.from(rowOf(G.in, i)).sort((x, y) => (G.cited_all[y] - G.cited_all[x]) || (x - y));
    const out = nodeObj(i);
    Object.assign(out, { html, cites: cites.map(nodeObj), cited_by: citedBy.map(nodeObj), cited_by_total: citedBy.length, text_stats: stats });
    if (!html) out.note = 'no CAP text for this case (post-2020 or unmatched)';
    caseCache.set(cl, out);
    return out;
  }

  // ---------------------------------------------------------------- CAP html -> opinion body (port of cap_text.py)
  const DATA_BLOCKS_RE = /\s+data-blocks='[^']*'/g;
  const ATTORNEYS_RE = /<p class="attorneys"[^>]*>.*?<\/p>/gs;
  const IMG_RE = /<img[^>]*>/g;
  const PAGE_LABEL_RE = /<a [^>]*class="page-label"[^>]*>(.*?)<\/a>/gs;
  const CAP_CITE_RE = /<a ([^>]*class="citation"[^>]*)>(.*?)<\/a>/gs;
  const ATTR_RE = /([\w-]+)="([^"]*)"/g;
  const CITE_LINK_RE = /<a class="cite" data-id="(\d+)">/g;
  const ABBR = '(?:Corp|Assn|Dept|Bros|Natl|Comm|Commn|Admin|Indus|Hosp|Univ|Educ|Assoc|Distrib|Transp|Mfrs)';
  const TOK = "(?:[A-Z][A-Za-z0-9'’&\\-]*(?:\\.[A-Z][A-Za-z0-9'’&\\-]*)*(?:(?<![A-Za-z]{6})\\.)?|" + ABBR + '\\.|&amp;|of|the|and|de|du|des|for|ex rel\\.|et al\\.|et ux\\.|a|an)';
  const SEP = '(?:\\s|</?em>)+';
  const PARTY = `${TOK}(?:(?:,\\s+(?=[A-Z])|${SEP})${TOK})*`;
  const NAME = `(?:${PARTY}${SEP}v\\.${SEP}${PARTY}|(?:Ex parte|In re|Matter of|In the Matter of)${SEP}${PARTY})`;
  const PREFIX_RE = new RegExp(`(?:<em>)?${NAME},?(?:\\s|</?em>)*$`);
  const SIGNAL_RE = new RegExp('^(?:<em>)?(?:See also|See, e\\.g\\.,|See|Cf\\.|Compare|But see|But cf\\.|Accord|E\\.g\\.,|E\\.g\\.|In|And|Also|' +
    'But|Contra|Quoting|Citing|Under|Unlike|Like|Both|Thus|Hence|Here|Or|Nor|For|The|That|This|With|As|' +
    'Of|On|Since|Where|When|While|Although|Because|If|Our|Its|His|Her|First|Second|Third|Fourth|Finally|' +
    'Then|Again|Indeed|Moreover|However|Therefore|Accordingly|of|the|and|a|an|for|de|du|des)\\.?(?:\\s|</?em>)+');
  const IN_RE_START = /^(?:<em>)?(?:Ex parte|In re|Matter of|In the Matter of)/;

  function resolveCaps(idsAttr, selfIdx) {
    // CAP case ids -> exactly one graph node (not the case itself) or null; returns the node index
    const found = new Set();
    for (const s of idsAttr.split(/[,\s]+/)) {
      if (!s) continue;
      const idx = G.capToIdx.get(+s);
      if (idx != null && idx !== selfIdx) found.add(idx);
    }
    return found.size === 1 ? found.values().next().value : null;
  }

  function linkify(raw, selfIdx) {
    let h = raw.replace(DATA_BLOCKS_RE, '').replace(ATTORNEYS_RE, '').replace(IMG_RE, '')
      .replace(PAGE_LABEL_RE, (m, inner) => '<span class="page-label">' + inner.trim() + '</span>');
    const stats = { cap_anchors: 0, links: 0, linked_ids: new Set() };

    // pass 1: CAP's own citation anchors
    h = h.replace(CAP_CITE_RE, (m, attrs, inner) => {
      stats.cap_anchors++;
      let ids = '';
      for (const a of attrs.matchAll(ATTR_RE)) if (a[1] === 'data-case-ids') ids = a[2];
      const idx = resolveCaps(ids, selfIdx);
      if (idx == null) return inner;
      stats.links++; stats.linked_ids.add(G.ids[idx]);
      return `<a class="cite" data-id="${G.ids[idx]}">${inner}</a>`;
    });
    // (pass 2 of cap_text.py, cites_to strings CAP did not wrap, needs the json sidecar, which the archive does not serve)

    // pass 3: pull an immediately preceding "Xxx v. Yyy, " into each link
    const out = [];
    let pos = 0;
    for (const m of h.matchAll(CITE_LINK_RE)) {
      const start = m.index;
      const windowStart = Math.max(pos, start - 300);
      const pm = PREFIX_RE.exec(h.slice(windowStart, start));
      let prefix = '';
      if (pm) {
        prefix = pm[0];
        for (let k = 0; k < 4; k++) prefix = prefix.replace(SIGNAL_RE, s => (s.startsWith('<em>') ? '<em>' : ''));
        if (prefix === '<em>' || !prefix.trim() || (!prefix.includes('v.') && !IN_RE_START.test(prefix))) prefix = '';
      }
      if (prefix) {
        const opens = (prefix.match(/<em>/g) || []).length, closes = (prefix.match(/<\/em>/g) || []).length;
        let pstart = start - prefix.length;
        if (closes > opens) {
          const before = h.slice(Math.max(pos, pstart - 12), pstart);
          const bm = /<em>\s*$/.exec(before);
          if (bm && closes - opens === 1) { pstart -= bm[0].length; prefix = h.slice(pstart, start); }
          else prefix = '';
        } else if (opens > closes) prefix = '';
      }
      if (prefix) {
        const pstart = start - prefix.length;
        out.push(h.slice(pos, pstart), m[0], prefix);
      } else out.push(h.slice(pos, start), m[0]);
      pos = start + m[0].length;
    }
    out.push(h.slice(pos));
    stats.linked_ids = Array.from(stats.linked_ids).sort((a, b) => a - b);
    return [out.join(''), stats];
  }

  // ---------------------------------------------------------------- routing
  function qInt(qs, key, dflt) {
    const v = qs.get(key);
    if (v == null || v === '') { if (dflt == null) throw new ApiError(400, `missing ${key}`); return dflt; }
    if (!/^-?\d+$/.test(v)) throw new ApiError(400, `${key} must be an integer`);
    return +v;
  }
  function qMode(qs) {
    const m = qs.get('mode') || 'any';
    if (!MODES.includes(m)) throw new ApiError(400, 'mode must be any, back or forward');
    return m;
  }
  function qNode(qs, key) {
    const cl = qInt(qs, key), i = G.byCl.get(cl);
    if (i == null) throw new ApiError(404, `${key}=${cl} is not a node of the game graph`);
    return i;
  }

  async function call(path) {
    await load();
    const u = new URL(path, 'http://static.invalid/');
    const parts = decodeURIComponent(u.pathname).replace(/^\/+|\/+$/g, '').split('/'); // ['api', ...]
    const qs = u.searchParams;
    if (parts[0] !== 'api') throw new ApiError(404, 'unknown API route');
    const rest = parts.slice(1).join('/');
    if (rest === 'starters') return apiStarters(qMode(qs));
    if (rest === 'puzzle') {
      const seed = qInt(qs, 'seed', 1), mode = qMode(qs), pair = qs.get('pair') || '';
      return pair ? apiPairPuzzle(pair, mode) : apiPuzzle(seed, mode);
    }
    if (rest === 'path') return apiPath(qNode(qs, 'from'), qNode(qs, 'to'), qMode(qs));
    if (rest === 'opponent') {
      const visited = new Set();
      for (let v of (qs.get('visited') || '').split(',')) {
        v = v.trim();
        if (!v) continue;
        if (!/^\d+$/.test(v)) throw new ApiError(400, 'visited must be comma-separated ids');
        const i = G.byCl.get(+v);
        if (i != null) visited.add(i);
      }
      return apiOpponent(qInt(qs, 'puzzle', 0), qNode(qs, 'at'), qNode(qs, 'target'), visited, qMode(qs));
    }
    if (parts.length === 3 && parts[1] === 'case') {
      if (!/^\d+$/.test(parts[2])) throw new ApiError(400, 'case id must be an integer');
      const i = G.byCl.get(+parts[2]);
      if (i == null) throw new ApiError(404, `${parts[2]} is not a node of the game graph (unknown, isolated, or a boilerplate hub)`);
      return apiCase(i);
    }
    if (rest === 'stats') return Object.assign({ eligible: G.eligible.length, cap_to_cl: G.capToIdx.size }, G.meta || {});
    throw new ApiError(404, 'unknown API route');
  }

  const StaticApi = {
    get enabled() {
      try { return !!(document.body && document.body.dataset && document.body.dataset.static); } catch (e) { return false; }
    },
    base: null,          // override the URL data/ is resolved against (defaults to the page)
    call,
    load,
    case: async cl => { await load(); const i = G.byCl.get(+cl); if (i == null) throw new ApiError(404, `${cl} is not a node of the game graph`); return apiCase(i); },
    linkify: async (raw, cl) => { await load(); return linkify(raw, cl == null ? null : G.byCl.get(+cl)); },
    ApiError,
    get graph() { return G; },
  };
  const root = typeof window !== 'undefined' ? window : globalThis;
  root.StaticApi = StaticApi;
})();

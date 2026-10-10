// Smoke test for app/static-api.js under node (no DOM).
//   node scripts/static_smoke.mjs [base-url] [reference-dir]
// base-url defaults to http://127.0.0.1:8777/ (python -m http.server 8777 from docs/).
// With reference-dir, every ref_<clid>.html in it (cap_text.py output with an empty cites_to
// list) is compared byte for byte against the JS linkify of the archive copy.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const base = process.argv[2] || 'http://127.0.0.1:8777/';
const refDir = process.argv[3] || '';

globalThis.window = globalThis;
globalThis.document = { body: { dataset: { static: '1' } }, baseURI: base };
vm.runInThisContext(fs.readFileSync(path.join(here, '..', 'app', 'static-api.js'), 'utf8'), { filename: 'static-api.js' });

const api = globalThis.StaticApi;
let failures = 0;
function check(label, ok, detail) {
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${label}${detail ? ' - ' + detail : ''}`);
  if (!ok) failures++;
}
const isNode = n => n && Number.isInteger(n.id) && typeof n.name === 'string' && Number.isInteger(n.year)
  && 'cite' in n && 'date' in n && 'cited_all' in n && 'cited_scotus' in n && typeof n.has_text === 'boolean';

check('enabled', api.enabled === true);
let t = Date.now();
await api.load();
const G = api.graph;
check('graph loaded', G.n === G.ids.length && G.edges.length / 2 === G.meta.edges, `${G.n} nodes, ${G.edges.length / 2} edges, ${Date.now() - t} ms`);

// puzzle, seed 1, each mode
for (const mode of ['any', 'back', 'forward']) {
  const p = await api.call(`/api/puzzle?seed=1&mode=${mode}`);
  const again = await api.call(`/api/puzzle?seed=1&mode=${mode}`);
  const pp = await api.call(`/api/path?from=${p.start.id}&to=${p.target.id}&mode=${mode}`);
  check(`puzzle seed=1 ${mode}`, isNode(p.start) && isNode(p.target) && p.shortest >= 3 && p.shortest <= 5 && p.par === p.shortest + 2
    && p.start.has_text && p.target.has_text && pp.length === p.shortest && again.start.id === p.start.id && again.target.id === p.target.id,
    `${p.start.name} (${p.start.year}) -> ${p.target.name} (${p.target.year}), shortest ${p.shortest}, par ${p.par}, path says ${pp.length}`);
  const p2 = await api.call(`/api/puzzle?seed=2&mode=${mode}`);
  check(`puzzle seed=2 ${mode} differs from seed 1`, p2.start.id !== p.start.id || p2.target.id !== p.target.id);
}

// starters
const st = await api.call('/api/starters?mode=any');
check('starters any has 26 entries', st.length === 26, `${st.length}`);
check('starters entries are shaped', st.every(s => isNode(s.start) && isNode(s.target) && s.pair === `${s.start.id}-${s.target.id}` && s.par === (s.shortest === 1 ? 1 : s.shortest + 2) && s.mode === 'any' && s.seed === 0 && s.group && s.theme));
for (const mode of ['back', 'forward']) {
  const l = await api.call(`/api/starters?mode=${mode}`);
  check(`starters ${mode} orient start/target`, l.every(s => mode === 'back' ? s.start.year >= s.target.year : s.start.year <= s.target.year), `${l.length} entries`);
}
// path for every starter pair matches its known shortest, in every mode
let pathOk = 0, pathN = 0;
for (const mode of ['any', 'back', 'forward']) {
  for (const s of await api.call(`/api/starters?mode=${mode}`)) {
    pathN++;
    const r = await api.call(`/api/path?from=${s.start.id}&to=${s.target.id}&mode=${mode}`);
    const q = await api.call(`/api/puzzle?pair=${s.pair}&mode=${mode}`);
    if (r.length === s.shortest && r.path.length === r.length + 1 && r.path[0].id === s.start.id && r.path[r.length].id === s.target.id && q.shortest === s.shortest && q.pair === s.pair) pathOk++;
    else console.log(`   mismatch ${mode} ${s.start.name} -> ${s.target.name}: starters ${s.shortest}, path ${r.length}, pair puzzle ${q.shortest}`);
  }
}
check('path for starter pairs returns the known shortest', pathOk === pathN, `${pathOk}/${pathN}`);
const erie = st.find(s => s.start.name.startsWith('Erie'));
const ep = await api.call(`/api/path?from=${erie.start.id}&to=${erie.target.id}&mode=any`);
console.log('     ' + ep.path.map(n => `${n.name} (${n.year})`).join(' -> '));
const nopath = await api.call(`/api/path?from=${erie.start.id}&to=${erie.target.id}&mode=back`);
check('path against time in back mode is null', nopath.length === null);

// opponent
const p1 = await api.call('/api/puzzle?seed=1&mode=any');
const o1 = await api.call(`/api/opponent?puzzle=1&at=${p1.start.id}&target=${p1.target.id}&visited=${p1.start.id}&mode=any`);
const o2 = await api.call(`/api/opponent?puzzle=1&at=${p1.start.id}&target=${p1.target.id}&visited=${p1.start.id}&mode=any`);
check('opponent returns a move', isNode(o1.move) && /^stand-in/.test(o1.note) && o1.move.id !== p1.start.id, `${o1.move && o1.move.name}, ${o1.note}`);
check('opponent is deterministic', o2.move.id === o1.move.id);
const o3 = await api.call(`/api/opponent?puzzle=1&at=${p1.start.id}&target=${p1.target.id}&visited=${p1.start.id},${o1.move.id}&mode=any`);
check('opponent never revisits', o3.move === null || (o3.move.id !== o1.move.id && o3.move.id !== p1.start.id));
// walk the stand-in to the target in back mode from a starter to see it can finish
{
  const s = (await api.call('/api/starters?mode=back'))[0];
  let at = s.start.id; const visited = [at]; let hops = 0;
  while (at !== s.target.id && hops < 12) {
    const r = await api.call(`/api/opponent?puzzle=0&at=${at}&target=${s.target.id}&visited=${visited.join(',')}&mode=back`);
    if (!r.move) break;
    at = r.move.id; visited.push(at); hops++;
  }
  check('opponent walk (back mode, starter 1)', hops > 0, `${hops} hops, reached target: ${at === s.target.id}`);
}

// errors
for (const [p, status] of [['/api/case/1', 404], ['/api/puzzle?mode=sideways', 400], ['/api/path?from=1&to=2', 404], ['/api/nope', 404], ['/api/puzzle?pair=1-2&mode=any', 404]]) {
  let got = null;
  try { await api.call(p); } catch (e) { got = e.status; }
  check(`error ${p} -> ${status}`, got === status, `got ${got}`);
}

// case: Erie from the archive
t = Date.now();
const c = await api.call('/api/case/103012');
const links = (c.html.match(/<a class="cite" data-id="\d+">/g) || []).length;
check('case 103012 (Erie) fetched and linkified', c.id === 103012 && c.has_text && c.html.length > 10000 && links > 50
  && !c.html.includes('data-blocks') && !c.html.includes('class="attorneys"') && !c.html.includes('class="citation"') && !c.html.includes('<img'),
  `${c.html.length} chars, ${links} links, ${c.cites.length} cites, ${c.cited_by.length} cited_by, ${Date.now() - t} ms`);
check('case lists are sorted', c.cites.every((n, i) => i === 0 || c.cites[i - 1].year <= n.year) && c.cited_by.every((n, i) => i === 0 || c.cited_by[i - 1].cited_all >= n.cited_all) && c.cited_by_total === c.cited_by.length);
check('case links point at graph nodes', [...c.html.matchAll(/data-id="(\d+)"/g)].every(m => G.byCl.has(+m[1])));
const swift = c.html.includes('<a class="cite" data-id="86188"><em>Swift </em>v. <em>Tyson, </em>16 Pet. 1</a>');
const named = (c.html.match(/<a class="cite" data-id="\d+">(?:<em>)?[^<]*<\/em>v\. <em>[^<]*<\/em>[^<]*<\/a>/g) || []).length;
check('case name pulled into the link (Swift v. Tyson, 16 Pet. 1)', swift && named > 20, `${named} links carry a case name`);
t = Date.now();
await api.call('/api/case/103012');
check('case is cached', Date.now() - t < 5, `${Date.now() - t} ms`);
// a node without text
const noText = G.ids[G.has_text.findIndex(x => !x)];
const n = await api.call(`/api/case/${noText}`);
check('case without text returns html "" and has_text false', n.html === '' && n.has_text === false && n.note, `${n.name} (${n.year})`);

// parity with cap_text.py, when reference renderings are supplied
if (refDir) {
  for (const f of fs.readdirSync(refDir).filter(f => /^ref_\d+\.html$/.test(f))) {
    const cl = +f.slice(4, -5);
    const ref = fs.readFileSync(path.join(refDir, f), 'utf8');
    const got = (await api.call(`/api/case/${cl}`)).html;
    let d = 0; while (d < ref.length && ref[d] === got[d]) d++;
    check(`parity with cap_text.py for ${cl}`, got === ref, got === ref ? `${ref.length} chars` : `first difference at ${d}: ref ...${JSON.stringify(ref.slice(d - 60, d + 40))} got ...${JSON.stringify(got.slice(d - 60, d + 40))}`);
  }
}

console.log(failures ? `\n${failures} failure(s)` : '\nall checks passed');
process.exit(failures ? 1 : 0);

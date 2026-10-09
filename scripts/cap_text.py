"""Turn a CAP case HTML member into the opinion body served by /api/case/<id>.

CAP's html/<page>-<n>.html is a <section class="casebody"> with head-matter, one <article
class="opinion"> per opinion (majority, concurrence, dissent, in order) and <aside
class="footnote"> blocks. Citation strings are already wrapped by CAP as
<a class="citation" data-cite=".." data-case-ids="..">264 U. S. 182</a>, so the main pass
rewrites those anchors; a second pass scans text nodes for any cites_to string CAP
did not wrap. Only cites that resolve to a node of the game graph become
<a class="cite" data-id="<cl id>">...</a>; everything else is unwrapped to plain text.
"""
import html as html_mod
import re

DATA_BLOCKS_RE = re.compile(r"\s+data-blocks='[^']*'")
ATTORNEYS_RE = re.compile(r"<p class=\"attorneys\"[^>]*>.*?</p>", re.S)
IMG_RE = re.compile(r"<img[^>]*>")
PAGE_LABEL_RE = re.compile(r"<a [^>]*class=\"page-label\"[^>]*>(.*?)</a>", re.S)
PAGE_LABEL_NUM_RE = re.compile(r"data-label=\"([^\"]*)\"")
CAP_CITE_RE = re.compile(r"<a ([^>]*class=\"citation\"[^>]*)>(.*?)</a>", re.S)
ATTR_RE = re.compile(r"([\w-]+)=\"([^\"]*)\"")
TAG_SPLIT_RE = re.compile(r"(<[^>]+>)")
CITE_LINK_RE = re.compile(r"<a class=\"cite\" data-id=\"(\d+)\">")

# case-name prefix immediately before a cite link: "Xxx v. Yyy, " (em tags tolerated)
# a capitalised word; a trailing period is allowed only for short words / known abbreviations,
# so "Holmes. United Zinc Co. v. Britt" breaks at the sentence boundary
_ABBR = r"(?:Corp|Assn|Dept|Bros|Natl|Comm|Commn|Admin|Indus|Hosp|Univ|Educ|Assoc|Distrib|Transp|Mfrs)"
_TOK = (r"(?:[A-Z][A-Za-z0-9'’&\-]*(?:\.[A-Z][A-Za-z0-9'’&\-]*)*"
        r"(?:(?<![A-Za-z]{6})\.)?|" + _ABBR + r"\.|&amp;|of|the|and|de|du|des|for|ex rel\.|et al\.|et ux\.|a|an)")
_SEP = r"(?:\s|</?em>)+"
_PARTY = rf"{_TOK}(?:(?:,\s+(?=[A-Z])|{_SEP}){_TOK})*"
_NAME = rf"(?:{_PARTY}{_SEP}v\.{_SEP}{_PARTY}|(?:Ex parte|In re|Matter of|In the Matter of){_SEP}{_PARTY})"
PREFIX_RE = re.compile(rf"(?:<em>)?{_NAME},?(?:\s|</?em>)*$")
SIGNAL_RE = re.compile(
    r"^(?:<em>)?(?:See also|See, e\.g\.,|See|Cf\.|Compare|But see|But cf\.|Accord|E\.g\.,|E\.g\.|In|And|Also|"
    r"But|Contra|Quoting|Citing|Under|Unlike|Like|Both|Thus|Hence|Here|Or|Nor|For|The|That|This|With|As|"
    r"Of|On|Since|Where|When|While|Although|Because|If|Our|Its|His|Her|First|Second|Third|Fourth|Finally|"
    r"Then|Again|Indeed|Moreover|However|Therefore|Accordingly|of|the|and|a|an|for|de|du|des)\.?(?:\s|</?em>)+")
WS_RE = re.compile(r"\s+")


def _norm(s):
    return WS_RE.sub(" ", html_mod.unescape(s)).strip()


def _resolve(case_ids, resolver, self_id):
    """case_ids: iterable of CAP ids -> a single CL node id or None."""
    found = set()
    for cap_id in case_ids:
        try:
            cl = resolver(int(cap_id))
        except (TypeError, ValueError):
            cl = None
        if cl is not None and cl != self_id:
            found.add(cl)
    return found.pop() if len(found) == 1 else None


def render(raw_html, cites_to, resolver, self_id=None):
    """raw_html: str; cites_to: CAP cites_to list; resolver(cap_id) -> cl id in the graph or None.
    Returns (html, stats)."""
    h = raw_html
    h = DATA_BLOCKS_RE.sub("", h)
    h = ATTORNEYS_RE.sub("", h)
    h = IMG_RE.sub("", h)
    h = PAGE_LABEL_RE.sub(lambda m: '<span class="page-label">' + m.group(1).strip() + "</span>", h)

    stats = {"cites_to": len(cites_to or []), "cites_to_cases": 0, "cites_to_resolved": 0,
             "cap_anchors": 0, "links": 0, "links_text_pass": 0, "linked_ids": set()}
    wrapped_strings = set()

    # pass 1: CAP's own citation anchors
    def repl_anchor(m):
        attrs = dict(ATTR_RE.findall(m.group(1)))
        inner = m.group(2)
        stats["cap_anchors"] += 1
        wrapped_strings.add(_norm(inner))
        ids = [x for x in re.split(r"[,\s]+", attrs.get("data-case-ids", "")) if x]
        cl = _resolve(ids, resolver, self_id)
        if cl is None:
            return inner
        stats["links"] += 1
        stats["linked_ids"].add(cl)
        return f'<a class="cite" data-id="{cl}">{inner}</a>'
    h = CAP_CITE_RE.sub(repl_anchor, h)

    # pass 2: cites_to strings CAP did not wrap, replaced in text nodes outside any <a>
    todo = []
    for ct in cites_to or []:
        ids = ct.get("case_ids") or []
        if not ids:
            continue
        stats["cites_to_cases"] += 1
        cl = _resolve(ids, resolver, self_id)
        if cl is None:
            continue
        stats["cites_to_resolved"] += 1
        s = _norm(ct.get("cite", ""))
        if s and s not in wrapped_strings:
            todo.append((s, cl))
    if todo:
        todo.sort(key=lambda t: -len(t[0]))
        parts = TAG_SPLIT_RE.split(h)
        depth = 0
        for i, seg in enumerate(parts):
            if i % 2 == 1:  # a tag
                low = seg[:3].lower()
                if low == "<a " or seg.lower() == "<a>":
                    depth += 1
                elif low == "</a":
                    depth = max(0, depth - 1)
                continue
            if depth or not seg.strip():
                continue
            for s, cl in todo:
                esc = html_mod.escape(s, quote=False)
                pat = re.compile(r"(?<![\w])" + r"\s+".join(re.escape(w) for w in esc.split()) + r"(?![\w])")
                def repl(m, cl=cl):
                    stats["links"] += 1
                    stats["links_text_pass"] += 1
                    stats["linked_ids"].add(cl)
                    return f'<a class="cite" data-id="{cl}">{m.group(0)}</a>'
                seg = pat.sub(repl, seg)
            parts[i] = seg
        h = "".join(parts)

    # pass 3: pull an immediately preceding "Xxx v. Yyy, " into each link
    out, pos = [], 0
    for m in CITE_LINK_RE.finditer(h):
        start = m.start()
        window_start = max(pos, start - 300)
        window = h[window_start:start]
        pm = PREFIX_RE.search(window)
        if pm:
            prefix = pm.group(0)
            for _ in range(4):
                prefix = SIGNAL_RE.sub(lambda s: "<em>" if s.group(0).startswith("<em>") else "", prefix)
            if prefix == "<em>" or not prefix.strip() or "v." not in prefix and not re.match(
                    r"(?:<em>)?(?:Ex parte|In re|Matter of|In the Matter of)", prefix):
                prefix = ""
        else:
            prefix = ""
        if prefix:
            opens, closes = prefix.count("<em>"), prefix.count("</em>")
            pstart = start - len(prefix)
            if closes > opens:
                before = h[max(pos, pstart - 12):pstart]
                bm = re.search(r"<em>\s*$", before)
                if bm and closes - opens == 1:
                    pstart -= len(bm.group(0))
                    prefix = h[pstart:start]
                else:
                    prefix = ""
            elif opens > closes:
                prefix = ""
        if prefix:
            pstart = start - len(prefix)
            out.append(h[pos:pstart])
            out.append(m.group(0))
            out.append(prefix)
        else:
            out.append(h[pos:start])
            out.append(m.group(0))
        pos = m.end()
    out.append(h[pos:])
    h = "".join(out)

    stats["linked_ids"] = sorted(stats["linked_ids"])
    return h, stats

#!/usr/bin/env python
"""Build a SCOTUS-only citation graph from CAP static bulk zips (static.case.law).

Reads data/cap/raw/<reporter>/<vol>.zip (each zip holds metadata/CasesMetadata.json
with a `cites_to` array per case), and writes:

  data/cap/scotus_nodes.csv          one row per SCOTUS case (U.S. Reports vols 1-572,
                                     plus S. Ct. vols 134-140 for cases not already in U.S.)
  data/cap/scotus_edges.csv          citing_cap_id, cited_cap_id, weight, via
  data/cap/scotus_out_cites_all.csv  every cites_to entry from every SCOTUS case, any reporter
  data/cap/scotus_alias_sct_to_us.csv S. Ct. duplicates folded into their U.S. Reports node
  data/cap/build_summary.json        counts used in the write-up

Run with:  python -I scripts/cap_build_graph.py --raw data/cap/raw --out data/cap
The raw directory is untrusted download data: we only ever json.load() from it.
"""
import argparse, csv, glob, json, os, re, sys, zipfile
from collections import Counter, defaultdict

CITE_RE = re.compile(r"^\s*(\d+)\s+(.+?)\s+(\d+[A-Za-z\-]*)\s*$")


REP_SYNONYMS = {"dal": "dall", "dallas": "dall", "cr": "cranch", "wh": "wheat", "pet": "pet",
                "peters": "pet", "howard": "how", "wallace": "wall", "bl": "black"}


def rep_key(rep):
    """'U. S.' -> 'us'; 'Cranch, Rep.' -> 'cranch'; 'L. Ed. 2d' -> 'led2d'; 'Dallas' -> 'dall'."""
    k = re.sub(r"[^a-z0-9]", "", rep.lower())
    k = re.sub(r"rep$", "", k) or k
    return REP_SYNONYMS.get(k, k)


def parse_cite(s):
    """Return (vol:int, reporter_key, page:int) or None."""
    m = CITE_RE.match((s or "").replace(" ", " "))
    if not m:
        return None
    vol, rep, page = m.groups()
    pm = re.match(r"\d+", page)
    return int(vol), rep_key(rep), int(pm.group(0))


def norm_cite(s):
    p = parse_cite(s)
    return p if p else re.sub(r"\s+", " ", (s or "")).strip().lower()


def load_volumes(raw, reporter):
    files = sorted(glob.glob(os.path.join(raw, reporter, "*.zip")),
                   key=lambda p: int(os.path.basename(p).split(".")[0]))
    for path in files:
        vol = os.path.basename(path).split(".")[0]
        try:
            with zipfile.ZipFile(path) as z:
                data = json.loads(z.read("metadata/CasesMetadata.json").decode("utf-8"))
        except Exception as e:  # noqa
            print(f"WARN cannot read {path}: {e}", file=sys.stderr)
            continue
        for c in data:
            yield reporter, vol, c


def name_key(rec):
    return (rec["decision_date"], re.sub(r"\W+", "", (rec["case_name"] or "").lower()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-sct", action="store_true", help="skip the S. Ct. extension volumes")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    cases = {}  # cap_id -> record
    order = []  # cap_ids in load order
    cite_index = defaultdict(set)  # normalised cite string -> set(cap_id)
    led_index = defaultdict(set)   # L. Ed. / L. Ed. 2d cite -> set(cap_id) (for S. Ct. dedup)
    alias = {}  # dropped duplicate cap_id -> surviving cap_id
    summary = Counter()

    def make_rec(reporter, vol, c):
        cid = c["id"]
        cites = c.get("citations", [])
        official = next((x["cite"] for x in cites if x.get("type") == "official"), "")
        allc = [x["cite"] for x in cites]
        us = sct = led = ""
        other = []
        for x in allc:
            p = parse_cite(x)
            rep = p[1] if p else ""
            if rep == "us":
                us = us or x
            elif rep == "sct":
                sct = sct or x
            elif rep in ("led", "led2d"):
                led = led or x
            else:
                other.append(x)
        an = c.get("analysis") or {}
        rec = dict(
            cap_case_id=cid,
            case_name=c.get("name_abbreviation") or c.get("name"),
            case_name_full=c.get("name"),
            us_cite=us, sct_cite=sct, led_cite=led,
            other_cites="|".join(other),
            official_cite=official,
            decision_date=c.get("decision_date", "") or "",
            year=(c.get("decision_date") or "")[:4],
            docket_number=c.get("docket_number", ""),
            source_reporter=reporter, source_volume=vol,
            first_page=c.get("first_page", ""), last_page=c.get("last_page", ""),
            word_count=an.get("word_count", ""),
            cap_pagerank_pct=round((an.get("pagerank") or {}).get("percentile", 0) or 0, 6),
            n_cites_to=len(c.get("cites_to") or []),
            court=(c.get("court") or {}).get("name_abbreviation", ""),
            _cites_to=c.get("cites_to") or [],
        )
        return rec, allc, led

    # 1) U.S. Reports first (primary)
    for reporter, vol, c in load_volumes(args.raw, "us"):
        rec, allc, led = make_rec(reporter, vol, c)
        cid = rec["cap_case_id"]
        if rec["court"] != "U.S.":
            summary["dropped_non_scotus_court"] += 1
            summary["dropped_non_scotus_court_by_vol_" + vol] += 1
            continue
        if cid in cases:
            summary["dup_cap_id_in_us"] += 1
            continue
        cases[cid] = rec
        order.append(cid)
        for x in allc:
            cite_index[norm_cite(x)].add(cid)
        if led:
            led_index[norm_cite(led)].add(cid)
        summary["nodes_us"] += 1

    # 2) S. Ct. extension (vols 134-140). Drop any case already present in U.S. Reports,
    #    matched on the shared L. Ed. 2d parallel cite, else on (decision_date, name).
    name_date = {name_key(cases[cid]): cid for cid in order}
    if not args.no_sct:
        for reporter, vol, c in load_volumes(args.raw, "s-ct"):
            rec, allc, led = make_rec(reporter, vol, c)
            cid = rec["cap_case_id"]
            if rec["court"] != "U.S.":
                summary["dropped_non_scotus_court"] += 1
                continue
            if cid in cases:
                summary["sct_same_cap_id_as_us"] += 1
                continue
            target = None
            if led and len(led_index.get(norm_cite(led), ())) == 1:
                target = next(iter(led_index[norm_cite(led)]))
                summary["sct_dropped_dup_via_led"] += 1
            elif name_key(rec) in name_date:
                target = name_date[name_key(rec)]
                summary["sct_dropped_dup_via_name_date"] += 1
            if target is not None:
                alias[cid] = target
                for x in allc:  # make the U.S. node findable by its S. Ct. cite string too
                    cite_index[norm_cite(x)].add(target)
                if not cases[target]["sct_cite"] and rec["sct_cite"]:
                    cases[target]["sct_cite"] = rec["sct_cite"]
                continue
            cases[cid] = rec
            order.append(cid)
            for x in allc:
                cite_index[norm_cite(x)].add(cid)
            summary["nodes_sct_added"] += 1

    # Orders / cert-denial "cases": U.S. Reports (and S. Ct.) volumes include hundreds of
    # thousands of one-paragraph orders (e.g. 572 U.S. 1001, "cert. denied"). Many of them do
    # carry a cite (to the lower-court decision), so flag on length alone: < 300 words.
    for cid in order:
        r = cases[cid]
        wc = r["word_count"] if isinstance(r["word_count"], int) else 0
        r["is_order_like"] = int(wc < 300)

    # page-range index: (vol, reporter_key) -> [(first, last, cid)] for pin-cite resolution
    page_ranges = defaultdict(list)
    for cid in order:
        r = cases[cid]
        try:
            fp, lp = int(re.match(r"\d+", str(r["first_page"])).group(0)),                      int(re.match(r"\d+", str(r["last_page"])).group(0))
        except (AttributeError, ValueError, TypeError):
            continue
        for x in [r["us_cite"], r["sct_cite"]] + r["other_cites"].split("|"):
            p = parse_cite(x)
            if p and p[2] == fp:
                page_ranges[(p[0], p[1])].append((fp, lp, cid))

    def resolve_page_range(cite):
        p = parse_cite(cite)
        if not p:
            return None
        hits = {cid for fp, lp, cid in page_ranges.get((p[0], p[1]), ()) if fp <= p[2] <= lp}
        return next(iter(hits)) if len(hits) == 1 else None

    # 3) Edges
    edges = defaultdict(lambda: [0, set()])  # (citing, cited) -> [weight, via-set]
    out_all_path = os.path.join(args.out, "scotus_out_cites_all.csv")
    with open(out_all_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["citing_cap_id", "cite", "reporter", "category", "weight", "year",
                    "case_ids", "resolved_cap_id", "via", "opinion_index"])
        for cid in order:
            r = cases[cid]
            for t in r["_cites_to"]:
                weight = t.get("weight") or 1
                case_ids = t.get("case_ids") or []
                resolved, via = None, ""
                # path A: CAP's own case_ids
                for x in case_ids:
                    x = alias.get(x, x)
                    if x in cases:
                        resolved, via = x, "case_ids"
                        break
                # path B: cite string against our node table (U.S., S. Ct., L. Ed., nominative)
                if resolved is None:
                    hits = cite_index.get(norm_cite(t.get("cite", "")))
                    if hits:
                        if len(hits) == 1:
                            resolved, via = next(iter(hits)), "cite_string"
                        else:
                            via = "cite_ambiguous"
                            summary["out_cites_cite_ambiguous"] += 1
                # path C: cite string falls inside a node's page range (pin cite / wrong page)
                if resolved is None and via != "cite_ambiguous" and                         (t.get("category") or "").startswith("reporters"):
                    hit = resolve_page_range(t.get("cite", ""))
                    if hit is not None:
                        resolved, via = hit, "page_range"
                summary["out_cites_total"] += 1
                if (t.get("category") or "").startswith("reporters"):
                    summary["out_cites_to_reporters"] += 1
                if resolved is not None and resolved != cid:
                    e = edges[(cid, resolved)]
                    e[0] += weight
                    e[1].add(via)
                    summary[f"out_cites_resolved_via_{via}"] += 1
                elif resolved == cid:
                    summary["self_cites_skipped"] += 1
                elif case_ids:
                    summary["out_cites_case_ids_outside_scotus"] += 1
                w.writerow([cid, t.get("cite", ""), t.get("reporter", ""), t.get("category", ""),
                            weight, t.get("year", ""), "|".join(map(str, case_ids)),
                            resolved if resolved is not None else "", via,
                            t.get("opinion_index", "")])

    with open(os.path.join(args.out, "scotus_edges.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["citing_cap_id", "cited_cap_id", "weight", "via"])
        for (a, b), (wt, via) in sorted(edges.items()):
            w.writerow([a, b, wt, "+".join(sorted(via))])
    summary["edges_unique_pairs"] = len(edges)
    summary["edges_via_case_ids_only"] = sum(1 for v in edges.values() if v[1] == {"case_ids"})
    summary["edges_via_cite_string_only"] = sum(1 for v in edges.values() if v[1] == {"cite_string"})
    summary["edges_via_page_range_only"] = sum(1 for v in edges.values() if v[1] == {"page_range"})
    summary["edges_via_multiple_paths"] = sum(1 for v in edges.values() if len(v[1]) > 1)

    cols = ["cap_case_id", "case_name", "us_cite", "decision_date", "year", "sct_cite", "led_cite",
            "other_cites", "official_cite", "case_name_full", "docket_number", "source_reporter",
            "source_volume", "first_page", "last_page", "word_count", "cap_pagerank_pct",
            "n_cites_to", "is_order_like", "court"]
    with open(os.path.join(args.out, "scotus_nodes.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for cid in order:
            w.writerow(cases[cid])
    with open(os.path.join(args.out, "scotus_alias_sct_to_us.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sct_cap_id", "us_cap_id"])
        for a, b in sorted(alias.items()):
            w.writerow([a, b])

    summary["nodes_total"] = len(order)
    summary["nodes_order_like"] = sum(cases[c]["is_order_like"] for c in order)
    dates = sorted(cases[c]["decision_date"] for c in order if cases[c]["decision_date"])
    summary["min_decision_date"] = dates[0]
    summary["max_decision_date"] = dates[-1]
    us_dates = sorted(cases[c]["decision_date"] for c in order
                      if cases[c]["source_reporter"] == "us" and cases[c]["decision_date"])
    summary["max_decision_date_us_reports"] = us_dates[-1]
    summary["courts"] = dict(Counter(cases[c]["court"] for c in order))
    with open(os.path.join(args.out, "build_summary.json"), "w") as f:
        json.dump(dict(summary), f, indent=2, sort_keys=True)
    for k, v in sorted(summary.items()):
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()

"""Find famous-case pairs that are a short citation walk apart, as starter puzzles.

Usage: python -I scripts/starters.py [--max 3] [--mode any|back|forward]
Prints pairs among a canon of well-known Supreme Court cases whose shortest path is 2..max hops.
"""
import argparse, itertools, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve  # noqa: E402

CANON = """
5 U.S. 137|Marbury v. Madison
17 U.S. 316|McCulloch v. Maryland
22 U.S. 1|Gibbons v. Ogden
41 U.S. 1|Swift v. Tyson
60 U.S. 393|Dred Scott v. Sandford
71 U.S. 2|Ex parte Milligan
83 U.S. 36|Slaughter-House Cases
95 U.S. 714|Pennoyer v. Neff
109 U.S. 3|Civil Rights Cases
118 U.S. 356|Yick Wo v. Hopkins
163 U.S. 537|Plessy v. Ferguson
198 U.S. 45|Lochner v. New York
208 U.S. 412|Muller v. Oregon
249 U.S. 47|Schenck v. United States
274 U.S. 200|Buck v. Bell
283 U.S. 697|Near v. Minnesota
300 U.S. 379|West Coast Hotel v. Parrish
302 U.S. 319|Palko v. Connecticut
304 U.S. 64|Erie R. Co. v. Tompkins
304 U.S. 144|United States v. Carolene Products
317 U.S. 111|Wickard v. Filburn
319 U.S. 624|West Virginia v. Barnette
323 U.S. 214|Korematsu v. United States
326 U.S. 310|International Shoe v. Washington
341 U.S. 494|Dennis v. United States
343 U.S. 579|Youngstown Sheet & Tube v. Sawyer
347 U.S. 483|Brown v. Board of Education
367 U.S. 643|Mapp v. Ohio
369 U.S. 186|Baker v. Carr
370 U.S. 421|Engel v. Vitale
372 U.S. 335|Gideon v. Wainwright
376 U.S. 254|New York Times v. Sullivan
377 U.S. 533|Reynolds v. Sims
379 U.S. 241|Heart of Atlanta Motel v. United States
380 U.S. 460|Hanna v. Plumer
381 U.S. 479|Griswold v. Connecticut
384 U.S. 436|Miranda v. Arizona
388 U.S. 1|Loving v. Virginia
389 U.S. 347|Katz v. United States
392 U.S. 1|Terry v. Ohio
393 U.S. 503|Tinker v. Des Moines
395 U.S. 444|Brandenburg v. Ohio
403 U.S. 602|Lemon v. Kurtzman
403 U.S. 713|New York Times v. United States
408 U.S. 238|Furman v. Georgia
410 U.S. 113|Roe v. Wade
413 U.S. 15|Miller v. California
418 U.S. 683|United States v. Nixon
424 U.S. 1|Buckley v. Valeo
429 U.S. 190|Craig v. Boren
438 U.S. 265|Regents v. Bakke
466 U.S. 668|Strickland v. Washington
467 U.S. 837|Chevron v. NRDC
476 U.S. 79|Batson v. Kentucky
477 U.S. 242|Anderson v. Liberty Lobby
477 U.S. 317|Celotex v. Catrett
478 U.S. 186|Bowers v. Hardwick
484 U.S. 260|Hazelwood v. Kuhlmeier
491 U.S. 397|Texas v. Johnson
494 U.S. 872|Employment Division v. Smith
497 U.S. 261|Cruzan v. Director
504 U.S. 555|Lujan v. Defenders of Wildlife
505 U.S. 833|Planned Parenthood v. Casey
509 U.S. 579|Daubert v. Merrell Dow
514 U.S. 549|United States v. Lopez
517 U.S. 620|Romer v. Evans
520 U.S. 681|Clinton v. Jones
529 U.S. 598|United States v. Morrison
531 U.S. 98|Bush v. Gore
536 U.S. 304|Atkins v. Virginia
539 U.S. 306|Grutter v. Bollinger
539 U.S. 558|Lawrence v. Texas
542 U.S. 507|Hamdi v. Rumsfeld
543 U.S. 551|Roper v. Simmons
545 U.S. 1|Gonzales v. Raich
545 U.S. 469|Kelo v. New London
550 U.S. 544|Bell Atlantic v. Twombly
553 U.S. 723|Boumediene v. Bush
554 U.S. 570|District of Columbia v. Heller
556 U.S. 662|Ashcroft v. Iqbal
558 U.S. 310|Citizens United v. FEC
561 U.S. 742|McDonald v. Chicago
567 U.S. 519|NFIB v. Sebelius
570 U.S. 529|Shelby County v. Holder
570 U.S. 744|United States v. Windsor
573 U.S. 373|Riley v. California
573 U.S. 682|Burwell v. Hobby Lobby
576 U.S. 473|King v. Burwell
576 U.S. 644|Obergefell v. Hodges
584 U.S. 617|Masterpiece Cakeshop v. Colorado
585 U.S. 296|Carpenter v. United States
585 U.S. 667|Trump v. Hawaii
590 U.S. 644|Bostock v. Clayton County
"""


def find_ids():
    by_cite = {}
    for cid, n in serve.NODES.items():
        for c in n.get("cites_all", [n.get("cite")]) if isinstance(n.get("cites_all"), list) else [n.get("cite")]:
            if c:
                by_cite.setdefault(c.replace("U. S.", "U.S."), []).append(cid)
    found, missing = {}, []
    for line in CANON.strip().splitlines():
        cite, name = line.split("|")
        cands = by_cite.get(cite, [])
        # Several clusters can share a page (a real opinion and an order); prefer the real one whose name matches.
        toks = set(name.lower().replace(".", "").split()) - {"v", "the", "of"}
        cands.sort(key=lambda c: (-len(toks & set(serve.NODES[c]["name"].lower().replace(".", "").split())), -int(serve.NODES[c]["real"]), -serve.NODES[c]["cited_all"]))
        cid = cands[0] if cands else None
        if cid is None:
            # fall back to name match
            toks = set(name.lower().replace(".", "").split())
            best = None
            for c2, n in serve.NODES.items():
                if n.get("cite", "").split(" U.S.")[0] == cite.split(" U.S.")[0] and toks & set(n["name"].lower().split()):
                    best = c2; break
            cid = best
        if cid is None:
            missing.append(line)
        else:
            found[cid] = (cite, name, serve.NODES[cid])
    return found, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=3)
    ap.add_argument("--mode", default="any")
    args = ap.parse_args()
    serve.load()
    found, missing = find_ids()
    print(f"canon found {len(found)}, missing {len(missing)}", file=sys.stderr)
    for m in missing:
        print("  missing:", m, file=sys.stderr)
    ids = list(found)
    dists = {cid: serve.bfs_from(cid, args.mode, max_depth=args.max) for cid in ids}
    rows = []
    pairs = itertools.permutations(ids, 2) if args.mode != "any" else itertools.combinations(ids, 2)
    for a, b in pairs:
        d = dists[a].get(b)
        if d is not None and 2 <= d <= args.max:
            na, nb = found[a], found[b]
            if not (na[2]["has_text"] and nb[2]["has_text"] and na[2]["real"] and nb[2]["real"]):
                continue
            rows.append((d, na[1], na[2]["year"], nb[1], nb[2]["year"], a, b))
    rows.sort()
    for d, n1, y1, n2, y2, a, b in rows:
        print(f"{d}\t{n1} ({y1})\t{n2} ({y2})\t{a}\t{b}")


if __name__ == "__main__":
    main()

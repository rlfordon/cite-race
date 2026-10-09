"""Write data/prototype/starters.json: curated famous-case puzzles with per-mode shortest paths.
Usage: python -I scripts/make_starters.py
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve  # noqa: E402
import starters  # noqa: E402

# (older case, newer case, theme). Warm-ups are direct citations; the rest are 2 or 3 hops apart.
SETS = {
    "warm-up": [
        ("Plessy v. Ferguson", "Grutter v. Bollinger", "Separate to diverse"),
        ("Schenck v. United States", "Brandenburg v. Ohio", "Clear and present to imminent"),
        ("Gideon v. Wainwright", "Miranda v. Arizona", "Counsel to warnings"),
        ("Griswold v. Connecticut", "Obergefell v. Hodges", "Privacy to marriage"),
        ("Marbury v. Madison", "United States v. Nixon", "Judicial review to the tapes"),
        ("Wickard v. Filburn", "NFIB v. Sebelius", "Wheat to health care"),
        ("Near v. Minnesota", "New York Times v. United States", "Prior restraint"),
        ("Korematsu v. United States", "Hamdi v. Rumsfeld", "Wartime detention"),
    ],
    "starter": [
        ("Erie R. Co. v. Tompkins", "Bell Atlantic v. Twombly", "Civil procedure, start to finish"),
        ("Katz v. United States", "Kelo v. New London", "K to K"),
        ("Tinker v. Des Moines", "Citizens United v. FEC", "Armbands to super PACs"),
        ("Baker v. Carr", "Bush v. Gore", "The political thicket"),
        ("Mapp v. Ohio", "Carpenter v. United States", "Exclusion to location"),
        ("Celotex v. Catrett", "Ashcroft v. Iqbal", "Summary judgment to plausibility"),
        ("Yick Wo v. Hopkins", "Batson v. Kentucky", "Laundries to juries"),
        ("Engel v. Vitale", "Employment Division v. Smith", "Prayer to peyote"),
        ("Muller v. Oregon", "Craig v. Boren", "Women's hours to 3.2 beer"),
        ("Bowers v. Hardwick", "Carpenter v. United States", "Bedrooms to cell sites"),
    ],
    "three-hop": [
        ("Dred Scott v. Sandford", "Loving v. Virginia", "Citizenship to marriage"),
        ("Pennoyer v. Neff", "Carpenter v. United States", "Presence to cell towers"),
        ("Buck v. Bell", "Erie R. Co. v. Tompkins", "Holmes to Brandeis"),
        ("Civil Rights Cases", "Katz v. United States", "State action to phone booths"),
        ("Daubert v. Merrell Dow", "District of Columbia v. Heller", "Experts to arms"),
        ("Miranda v. Arizona", "Kelo v. New London", "Warnings to takings"),
        ("International Shoe v. Washington", "Daubert v. Merrell Dow", "Contacts to experts"),
        ("Ex parte Milligan", "Boumediene v. Bush", "Military tribunals"),
    ],
}


def main():
    serve.load()
    found, _ = starters.find_ids()
    by_name = {v[1]: k for k, v in found.items()}
    out = []
    for group, rows in SETS.items():
        for older, newer, theme in rows:
            a, b = by_name.get(older), by_name.get(newer)
            if a is None or b is None:
                print("missing", older, newer, file=sys.stderr)
                continue
            if serve.NODES[a]["year"] > serve.NODES[b]["year"]:
                a, b = b, a
            d = {
                "any": serve.bfs_from(a, "any", 8).get(b),
                "back": serve.bfs_from(b, "back", 8).get(a),      # start at the newer case, cite backward
                "forward": serve.bfs_from(a, "forward", 8).get(b),  # start at the older case, follow cited-by
            }
            out.append({"group": group, "theme": theme, "older": serve.node_obj(a), "newer": serve.node_obj(b), "shortest": d})
    path = os.path.join(serve.ROOT, "data", "prototype", "starters.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"wrote {len(out)} starters to {path}")
    for s in out:
        print(f"  [{s['group']}] {s['older']['name']} -> {s['newer']['name']}: any {s['shortest']['any']}, back {s['shortest']['back']}, fwd {s['shortest']['forward']}")


if __name__ == "__main__":
    main()

"""Boilerplate hub clusters excluded from the citation-race graph.

These are the most-cited SCOTUS "cases" in the CourtListener merged graph, but the
in-links are boilerplate, not doctrine (see notes/courtlistener-bulk.md, "Hubs, and
which ones are boilerplate"). serve.py removes them from the node set entirely before
computing the giant component, so they never appear in `cites`, `cited_by`, text links,
puzzles, paths or opponent moves.

Ids are CourtListener merged cluster ids (data/courtlistener/scotus_nodes_merged.csv).
Add a row to EXCLUSIONS to grow the list; `verify(nodes)` checks the ids still match.
"""

EXCLUSIONS = [
    # (cluster_id, us_cite, case_name, reason)
    (96405, "200 U.S. 321", "United States v. Detroit Timber & Lumber Co.",
     "cited by every syllabus ('The syllabus constitutes no part of the opinion...')"),
    (112790, "506 U.S. 1", "Martin v. District of Columbia Court of Appeals",
     "cited in every order denying in forma pauperis status to an abusive filer"),
    (111075, "464 U.S. 928", "Brown v. Herald Co.",
     "cited in every IFP-denial order alongside Martin"),
    (109532, "428 U.S. 153", "Gregg v. Georgia",
     "hub source: hundreds of 'adhering to our views' cert-denial dissents in capital cases"),
]

EXCLUDED_IDS = frozenset(row[0] for row in EXCLUSIONS)


def verify(nodes):
    """nodes: dict cluster_id -> row with 'us_cite'. Returns a list of mismatch strings."""
    problems = []
    for cid, cite, name, _ in EXCLUSIONS:
        row = nodes.get(cid)
        if row is None:
            problems.append(f"{cid} ({name}) not in node table")
        elif (row.get("us_cite") or "") != cite:
            problems.append(f"{cid} ({name}) has us_cite {row.get('us_cite')!r}, expected {cite!r}")
    return problems

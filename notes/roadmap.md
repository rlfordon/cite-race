# Roadmap (as of 2026-10-10)

What has been built, what has been talked about but not built, and the order to do it in. Sources: the working sessions of
2026-10-08 to 10-10 (local transcript plus the cloud sessions recorded in the commit messages), `notes/design-decisions.md`,
`notes/ideas.md`, `notes/prototype-backend.md` (known gaps) and the mockups. When an item ships, move it to "Done" with the
date. Anything said in a session and never written down belongs here as soon as it comes back to mind.

## Done

- 2026-10-09 Prototype: play screen, local server, static GitHub Pages build, live at rlfordon.github.io/cite-race.
- 2026-10-09 Docket start screen (one click to play), reporter page with pagination, find in opinion, hover syllabus cards,
  target peek dialog, chronology ladder with Jev revealed a hop behind, three direction modes, 26 curated starters.
- 2026-10-09 Phone layout: pinned bar, citator and trail as bottom sheets, tap-to-preview before a hop.
- 2026-10-10 Random puzzles draw notable targets (Wikipedia pageviews via `scripts/notoriety.py`, `docs/data/notable.json`)
  2 to 3 hops from the start, after playtesters found random pairs between obscure cases too hard.
- 2026-10-10 Jev precomputed with TypeSafe (`scripts/precompute_jev.py`, model jev-1.13.0) and replayed from
  `docs/data/jev.json`; random draws come from the pool Jev has raced. First run: 136 routes, 76 reached, 15,647 calls,
  about $0.60, 8 minutes at 6 workers.

## Now: judge Jev and settle par

The first run says the syllabus-only judgment is good on the canon and weak on random pairs:

| mode | starters reached | random pairs reached | note |
|---|---|---|---|
| any | 25 of 26 | 9 of 20 | 19 starters at the shortest path |
| back | 16 of 25 | 2 of 20 | gives up on 8 starters, mostly from Carpenter and Daubert |
| forward | 19 of 25 | 5 of 20 | |

Jev's chosen hops score a mean of 1.6 on the 0 to 4 scale, so it is mostly picking "same broad field" cases: the syllabus
of a candidate rarely says which way it leads. In the directed modes the lists are long and one wrong pick strands it.

1. Play a few starters and random puzzles against the real routes on the live site. Decide whether a 12-hop wander is
   fun to race or whether Jev should give up sooner.
2. Par as Jev's score (decided 2026-10-09, not built). The docket's par column becomes Jev's hop count, with a fallback
   when Jev did not finish: shortest plus two, or "Jev did not finish" shown as par 12. Needs a rule for the random row,
   whose Jev result is known too since the pool is fixed.
3. Store every candidate's score per hop, not only the chosen one, so the replay can show Jev's uncertainty strip (where
   it hesitated and where it was sure; the "machine assessment" language from the standing rules).
4. Try the question as a Choice over the candidate list instead of a Score per candidate, which is what the 2026-10-09
   session proposed: relative judgments are the strong kind. Cheaper too (one call per hop instead of up to 150).
5. Rerun whenever the graph or the starters change (routes are keyed by CourtListener ids). Grow `--pool` when 20 random
   puzzles per mode start to repeat. The cache in `data/jev/` means a rerun only pays for new questions.

## Next: citing-sentence contexts (one build, two uses) and Jev levels

Filed 2026-10-09 in `ideas.md`. Precompute, from the local CAP copy, the sentence around every citation anchor (about
300 chars per edge, 296k edges). This comes before hints and the map work because it improves what the player reads at
every hop and gives Jev the evidence it is missing at the same time.

1. Extraction script: for each edge, the citing sentence from the citing opinion. Ship as bundles of about 100 cases
   (one ~100 KB fetch per case opened, ~120 MB in the repo). Extraction output under `data/`, bundles under `docs/data/`.
2. Player: the citing sentence under each cited-by entry (like a citator) and under each cites entry (from the opinion on
   screen); the word filter searches those sentences as well as case names. This is the "filter by text" the 2026-10-09
   session asked for, in the shape that is light enough for the archive.
3. Jev: judge on the same windows. Today Jev sees only the target's syllabus beside each candidate's syllabus, never the
   case it stands on or why that case cites the candidate. A second judge scores the edge window against the target
   ("which of these most likely lies on the way to a case about X"); compare reached rate and hops with the syllabus
   version on the same pairs. The judgment then depends on the citing case, so the cache key changes.
4. Jev levels (2026-10-10): let the player choose how smart Jev is, on the docket next to the direction choice. The
   level is what Jev gets to read: the easy Jev reads syllabi (today's run), the smart Jev reads the citing sentences.
   Each level is its own precomputed route set, so `jev.json` gains a level key and par becomes per level. Other dials
   if two levels are not enough: the candidate cap per hop, the hop limit, or the stand-in as a level zero.
5. Full-text filtering of citing cases stays out of the static site (tens of MB per filter). The server version could use
   CourtListener's search API with `cites:`.

## Then: play features from the design sessions

- Hints: headnote-style topic reveals for the target, and Jev warmer/colder on the candidate list as a pairwise
  judgment. For static puzzles the warmer/colder hint can reuse the scores cached by the precompute.
- Daily puzzle: one shared pair per day, so a class races the same Jev on the same puzzle (2026-10-09 session).
- Local-only mode (hubs off): a teaching mode, not a difficulty setting; removing the top 100 hubs barely changes path
  length. In the night-lights framing this is the blackout.
- End-of-game record: the table of authorities, reads like the front of a brief, printable (mockups/reporter-shelf.html
  keeps the sketch). The replay should show your route beside Jev's and the shortest one.
- Night-lights map for the start screen and the replay (mockups/citation-highways.html, mockups/night-lights.html): light
  on lines not points, lamps coloured by era, almost no edges drawn, hubs visible from anywhere, the route reveal as the
  replay. The "wing view" variant (a small oblique map in one corner during play) was considered and set aside.
- Open questions from the first playtest, still unanswered: should backtracking cost a hop; is the citing list usable
  at a few hundred entries.
- Puzzle quality: check `any`-mode starts for out-degree so a start always has citations in its text; style pin cites
  and `Id.` links lower-key than the first cite to a case.
- Courtesies: a credit line for the Caselaw Access Project in the game's footer; a short note to the Library Innovation
  Lab about the teaching use.

## Later: data and text

- Post-2020 opinions have no text (`has_text: false`, about 1,750 nodes). A CourtListener text fallback would open them
  to puzzles but needs an API key, so it belongs to the server version or a small proxy.
- Known archive defects (ideas.md): Bivens begins mid-sentence in the CAP scan. Keep the list growing and point the same
  fallback at it.
- If static.case.law ever moves or closes browser access, host the Supreme Court subset (about 1.7 GB of HTML) elsewhere.
- Duplicate CourtListener clusters that share a cite but have no edge between them are both still in the graph.
- Case-name extension into the link is heuristic and stops early on some names.

## Parked: other directions

- Roadtrip with classic highway maps (ideas.md, references in `highway maps/`): two-ink printing on cream, route
  shields as citations, the hand-traced route in pen, strip maps showing one route. Parked 2026-10-08; revisit after
  the night-lights direction is judged on the start screen and replay.
- Route-claiming board game (a friend's idea, 2026-10-09): fixed board of famous cases, direct citations as roads,
  assignments to connect two cases, claim a road by finding the citation in the text. Classroom multiplayer, works on
  paper. Avoid the Ticket to Ride name, theme and card wording.
- Rejected for play, kept for reference: the shelf of volumes, the side-by-side thread of pages, glowing node graphs as
  the play surface.

## Order, in one line

Judge Jev and make par its score; build the citing sentences for player and Jev together, rerun Jev on them and offer
the two Jevs as levels; then hints, the daily puzzle, local-only mode and the end record; the map for start and replay
when the look is settled; data fallbacks when a key or proxy exists.

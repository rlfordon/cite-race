# What would make Citation Race fun and engaging (research, 2026-10-10)

Three research passes: link-chasing and daily-puzzle games; legal-research and research-skills teaching games; game
design on racing a non-reacting AI and on reading as play. Findings are mapped to this game; the roadmap carries the
order. Sources at the foot.

## Findings that change what to build

1. **Hops over clock.** Players of Wikipedia Speedruns prefer fewest-links to fastest; Redactle and Lichess Puzzle
   Streak have no timer. Plott's first legal-research race "was a flop" because one fast student always won and the
   others "didn't even have time to read the question"; the Kahoot literature (93 studies) lists the same complaints.
   Keep time as a tiebreaker only. In class, hide the clock.
2. **The middle of a route is where people quit.** Wikispeedia (30,000 human paths): 54% of games abandoned, about 10%
   drop-out at every click; the first hop (to a hub) and the last are easy, the middle stagnates; humans back-click
   about once per game; median human path 4 against optimal 3. The citing-sentence contexts and a coarse warmer/colder
   hint matter most mid-route. A "concede" button that still plays the replay turns giving up into an ending.
3. **Charge for backtracking, do not ban it.** "No back button" house rules are called infuriating; Wikispeedia counts
   back-clicks in the full path. This answers the open question: a step back costs a hop.
4. **A ghost is a readable line, not a rival.** Trackmania and Mario Kart players value ghosts for the line they teach.
   A ghost far behind or far ahead is dead weight; comparison motivates only when the gap feels closable. So: Jev gives
   up at about shortest + 3 rather than 12, "Jev gave up" is drawn as an event on the ladder, and the end record shows
   three numbers: your hops, Jev's, the shortest.
5. **Fixed beats adaptive.** Rubber-banding is resented because it erases a lead earned by playing well. Precomputed,
   non-reacting Jev is right. Difficulty comes from what Jev reads (the levels), never from handicapping the player.
6. **Visible hesitation makes an opponent beatable.** Pac-Man's ghosts are beatable because each habit is legible. Draw
   Jev's red dash thin where its top two candidates scored close and bold where it was sure; on hover, "Jev was torn
   between X and Y". This needs the per-candidate scores the roadmap already plans to store.
7. **Do not engineer near misses.** A 2021 experiment on racing avatars found narrow losses felt more boring than clear
   wins and did not raise persistence. Aim for legible outcomes and a next puzzle within reach.
8. **Scent per list entry.** Information-foraging theory: people scan labels and follow the one most like the goal.
   The hover syllabus is scent on demand; the citing sentence under each entry is scent at a glance, and the find box
   should search it. A 2025 WikiRace paper found a greedy agent on text similarity with loop-avoidance beat structural
   heuristics by an order of magnitude, which is also the diagnosis of Jev's 1.6 mean score.
9. **Coarse hints only.** Golden Idol and Obra Dinn validate in batches so guessing stays deductive. Warmer/colder must
   be per list or top-quartile, never per entry, or it becomes a path oracle.
10. **Mark the unexamined.** Outer Wilds marks log entries not fully read. Mark list entries whose card you have not
    hovered: it says what is unexamined without saying what matters.
11. **Self-explanation is where the learning lands.** Johnson and Mayer: menu-based reason prompts in a game improved
    learning; debriefs add roughly 18% in simulation games, written self-led debriefs most. A one-tap reason at each
    hop ("same doctrine", "cited for the rule I need", "landmark hub", "closer in time", "guess") written into the end
    record is the cheapest high-value addition, and makes the end record a memo a professor can grade.
12. **Leaderboards help the top and hurt the bottom.** Personal best and beating par or Jev by default; team totals
    only for class competition (Slavin's Teams-Games-Tournaments), never a public individual ranking.
13. **Games beat conventional teaching modestly and only under conditions.** Wouters et al. (77 studies): d = 0.29,
    larger with other instruction around it, repeated sessions and group play; Clark et al.: simpler visuals did as
    well or better. Short repeated rounds in pairs with a debrief; the photocopy look is not a liability.
14. **Name the real skill.** Print scavenger hunts drew contempt when disconnected from practice. Say in the game that
    the cited-by list is a citator's citing references, the filters are KeyCite and Shepard's filters, and the citing
    sentence is depth of treatment. The game then transfers by name.
15. **Silent playtests.** Golden Idol's team sat with mouths shut watching five to seven testers get stuck. Two
    students playing while you say nothing is the first test to run.
16. **The legal-research-game literature is anecdote.** RIPS, LWI and Law Library Journal pieces report attendance
    and enthusiasm; none measures learning. Citation Race could become the evidence by exporting routes client-side.

## Mechanics worth adding (static site, no accounts)

- **Daily puzzle** with a date seed drawn from the pool Jev has raced; first attempt recorded in localStorage; a modest
  streak of days finished at or under par shown on the docket. (Wordle: "it doesn't want any more of your time.")
- **Share string that is a string cite.** Not emoji: "Brown, 347 U.S. 483 → Bolling, 347 U.S. 497 → … (4 hops, Jev 6,
  par 5)", one row per hop, which doubles as the table of authorities and reads to lawyers who never saw the game.
- **Puzzle URLs** (`?from=…&to=…&mode=back`) so a professor assigns one link and pairs paste trails into a shared doc.
- **Streak mode**: random puzzles of rising shortest-path length, the run ends when you exceed par, one free backtrack
  (Lichess Puzzle Streak, Connections' four mistakes).
- **Named house rules** beside the direction choice: no Find, no syllabus card, hubs off (the Wikipedia "no United
  States page" and "no Ctrl-F" hardeners).
- **Three reference routes in the replay**: easy Jev, smart Jev, shortest, as medal lines (Trackmania's bronze, silver,
  gold ghosts); gate the smart Jev behind beating the easy one on a puzzle (Mario Kart's expert staff ghost).
- **Handcrafted red herrings** in the starters: pairs whose obvious hub (Brown, Marbury) is a dead end in the chosen
  mode (Connections is handmade so words seem to fit the wrong group).

## Ideas only case law makes possible

- **Treatment as terrain.** Flag cases later overruled or abrogated (the Constitution Annotated's table of overruled
  decisions is public and small). A "good law" mode: landing on an overruled case costs a hop, or the route must end on
  a case still good. Teaches Shepardizing by play; no Wikipedia analogue.
- **Chambers and era puzzles.** "Holmes to Scalia", "every hop a different author", "cross the Lochner era without
  landing in it": metadata CourtListener already carries, and a theme for random pairs.
- **Decided this day.** Daily targets decided on today's date, so the running head reads as the day's puzzle.

## Three classroom formats

1. **Pairs race and debrief, one period, works today.** Pairs on the same starter (the fixed pool means the same Jev
   route for everyone), three rounds of eight minutes; two pairs project their trail and justify each hop; the class
   compares with Jev and the shortest route. Closing prompt: which hop would a citator have given you faster?
2. **Team tournament, four weeks.** Heterogeneous teams of four; everyone plays the same three puzzles solo; team score
   is the sum of hops minus par, ties by time; screenshots or score strings submitted; only team totals posted; the last
   week hubs off.
3. **"Explain your route", graded homework.** A puzzle link; the student submits the printable table of authorities and a
   short memo: for each hop, why that citation and which cue (syllabus, year, citing sentence, hub), and one hop they
   would change after seeing Jev's route. Second attempt hubs off. Needs the end record and stable puzzle URLs.

## Sources

Navigation and daily puzzles: West and Leskovec, Human Wayfinding in Information Networks (WWW 2012),
https://archives.iw3c2.org/www2012/proceedings/proceedings/p619.pdf; West and Leskovec, Automatic vs Human Navigation
(ICWSM 2012), https://ojs.aaai.org/index.php/ICWSM/article/view/14238; HN on Wikipedia Speedruns,
https://news.ycombinator.com/item?id=32850856; Wikiracing house rules, https://en.wikipedia.org/wiki/Wikiracing; Wordle
origin, https://www.boston.com/news/national-news/2022/01/04/he-made-wordle-for-his-partner-now-its-an-online-hit/;
Iwata Asks on Mario Kart ghosts, https://www.nintendo.com/en-gb/Iwata-Asks/Iwata-Asks-Mario-Kart-Wii/Bringing-Racers-Together/5-Mario-Kart-goes-global/5-Mario-Kart-goes-global-214687.html;
Trackmania medal ghosts, https://steamcommunity.com/app/228760/discussions/2/630800444798168009; Lichess Puzzle Streak,
https://lichess.org/forum/general-chess-discussion/puzzle-streak-new-feature; Connections design,
https://vineyardgazette.com/news/2026/08/18/nyt-puzzle-makers-give-peek-behind-popular-games; Redactle rules,
https://redactle.anybrowser.org/how_to/; WikiRace textual agents (2025), https://arxiv.org/abs/2511.10585.

Game design: rubber-banding critique, https://www.cheatcc.com/articles/why-mario-kart-s-rubber-band-ai-feels-rigged-not-just-hard/;
dynamic difficulty review (Zohaib 2018), https://onlinelibrary.wiley.com/doi/10.1155/2018/5681652; Pac-Man Dossier,
https://www.gamedeveloper.com/pc/feature-the-i-pac-man-i-dossier; near misses in a video game (Finserås et al. 2021),
https://irep.ntu.ac.uk/id/eprint/36202; Hitman elusive targets,
https://gamedeveloper.com/design/designing-the-elusive-targets-system-in-2016-s-i-hitman-i-; daily runs,
https://www.gamedeveloper.com/design/the-24-hour-ticket-examining-daily-runs-; information scent,
https://jakobnielsenphd.substack.com/p/information-scent; Mark Brown on detective games,
https://gmtk.substack.com/p/what-makes-a-great-detective-game; Golden Idol postmortem,
https://www.gamedeveloper.com/design/case-of-the-golden-idol; leaderboard design,
https://yukaichou.com/gamification-analysis/leaderboard-design-definitive-guide-octalysis/.

Legal research and education: Plott, Gamifying Learning in Legal Research (RIPS 2025),
https://ripslawlibrarian.wordpress.com/2025/11/06/lets-have-some-fun-gamifying-learning-in-legal-research/; Haight,
Digital Escape Rooms (RIPS 2024), https://ripslawlibrarian.wordpress.com/2024/03/19/digital-escape-rooms-for-legal-research-review/;
Michels and Rosborough, Inescapable Skills (Can. L. Libr. Rev. 2024),
https://research.schulichlaw.dal.ca/en/publications/inescapable-skills-testing-legal-research-skills-in-an-escape-roo/;
Herr-Cardillo, Escape the Ordinary (LWI), https://www.lwionline.org/article/escape-ordinary-how-close-out-your-semester-challenging-escape-room-competition;
Vettorello, Resurrecting the Research Treasure Hunt, 109 Law Libr. J. (2017), https://repository.law.umich.edu/articles/1850;
Chester, Be Afraid (Slaw 2005), https://www.slaw.ca/2005/12/05/be-afraid-be-very-afraid/; KU Bluebook Relays,
https://bloglaw.ku.edu/race-wits-bluebook-relays-return-22nd-year; CALI Time Trial, https://www.cali.org/TimeTrial;
Wang and Tahir, Kahoot review (Computers & Education 2020), https://research.gold.ac.uk/id/eprint/39435; Wouters et al.
meta-analysis (J. Educ. Psych. 2013), https://research-portal.uu.nl/en/publications/a-meta-analysis-of-the-cognitive-and-motivational-effects-of-seri/;
Clark, Tanner-Smith and Killingsworth (RER 2016), https://www.sri.com/publication/education-learning-pubs/digital-learning-pubs/digital-games-design-and-learning-a-systematic-review-and-meta-analysis-brief/;
Johnson and Mayer on self-explanation prompts, https://cresst.org/publication/adding-self-explanation-prompts-to-an-educational-computer-game/;
debriefing and serious games, https://essay.utwente.nl/essays/92845; leaderboard effects,
https://repository.eduhk.hk/en/publications/the-winner-takes-it-all-effects-of-leaderboard-based-feedback-on-/;
Slavin on Teams-Games-Tournaments, https://link.springer.com/chapter/10.1007/978-3-319-45153-4_2.

Evidence quality: the Wikispeedia numbers, the Wardle and Iwata quotes, and the meta-analyses are primary. The
legal-research pieces are practitioner reports without measured learning. GeoGuessr and Sporcle claims are from
secondary write-ups.

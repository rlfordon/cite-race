# Citation Race

A legal research game for law students: get from one Supreme Court case to another by following citations, Wikipedia-race style, racing against Jev.

**Play it: https://rlfordon.github.io/cite-race/**

- **How it runs:** the GitHub Pages build in `docs/` runs entirely in the browser. The citation graph ships as JSON; opinion text is fetched per hop from the Caselaw Access Project archive at static.case.law.
- **Mechanic:** the opinion is the board. A citation in the text takes you back in time; the cited-by list takes you forward. Fewest hops wins. Par is the shortest path plus two (one-hop warm-ups are par 1).
- **Modes:** either direction, back in time only, forward in time only.

## Development

```
python -I scripts/serve.py        # local server with the full data (needs data/ built, see notes/)
python -I scripts/build_static.py # rebuild docs/ for Pages
```

The `data/` directory (CourtListener and CAP bulk pulls, about 10 GB) is not committed. `notes/` records the data pipeline, design decisions, and the API contract.

## Data

Citation graph from CourtListener bulk data (Free Law Project) and the Caselaw Access Project (Harvard Library Innovation Lab). Opinion text from static.case.law. See `notes/courtlistener-bulk.md` and `notes/cap-bulk.md`.

## License

Code is MIT licensed (see `LICENSE`). The citation graph in `docs/data` is derived from public court records as published by CourtListener (Free Law Project) and the Caselaw Access Project (Harvard Library Innovation Lab); opinion text is fetched at play time from static.case.law and is not redistributed here.

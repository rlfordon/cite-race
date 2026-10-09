#!/usr/bin/env bash
# Download CAP static bulk zips for the U.S. Reports reporter (vols 1-572) and
# the S. Ct. reporter extension (vols 134-140, 2013-2020) from static.case.law.
# Sequential, resumable (curl -C -), polite (short sleep between files).
# Usage: bash scripts/cap_download.sh [raw_dir]
set -u
RAW="${1:-C:/Users/Rebecca Fordon/Projects/cite-race/data/cap/raw}"
BASE="https://static.case.law"
UA="cite-race-classroom-project (rlfordon@gmail.com) curl"

fetch() { # fetch URL DEST
  local url="$1" dest="$2" tries=0
  while [ $tries -lt 5 ]; do
    curl -sS -L -A "$UA" -C - --retry 3 --retry-delay 5 -o "$dest" "$url" && return 0
    rc=$?
    # 416 / "range not satisfiable" when file already complete -> treat as done
    [ $rc -eq 33 ] && return 0
    tries=$((tries+1)); sleep 5
  done
  echo "FAILED $url" >&2; return 1
}

download_reporter() { # reporter first last
  local rep="$1" first="$2" last="$3"
  mkdir -p "$RAW/$rep"
  fetch "$BASE/$rep/ReporterMetadata.json" "$RAW/$rep/ReporterMetadata.json"
  fetch "$BASE/$rep/VolumesMetadata.json"  "$RAW/$rep/VolumesMetadata.json"
  for v in $(seq "$first" "$last"); do
    dest="$RAW/$rep/$v.zip"
    if [ -f "$dest.ok" ]; then continue; fi
    fetch "$BASE/$rep/$v.zip" "$dest" || continue
    # verify it is a readable zip before marking ok
    if python -I -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).testzip() is None or sys.exit(1)" "$dest"; then
      touch "$dest.ok"; echo "ok $rep/$v"
    else
      echo "BAD ZIP $rep/$v (will re-download next run)"; rm -f "$dest"
    fi
    sleep 0.3
  done
}

download_reporter us 1 572
download_reporter s-ct 134 140
echo DONE
du -sh "$RAW"

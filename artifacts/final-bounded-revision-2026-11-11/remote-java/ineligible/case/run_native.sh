#!/usr/bin/env bash
set -euo pipefail
STUDY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${1:-$RUNNER_TEMP/ekstazi-evidence}"
mkdir -p "$OUT_DIR"
cd "$STUDY_DIR"
export EKSTAZI_OUT="$OUT_DIR"
java -version > "$OUT_DIR/java-version.log" 2>&1
mvn -version > "$OUT_DIR/maven-version.log" 2>&1
run_case() {
  local label="$1"; shift
  local start=$SECONDS
  set +e
  mvn -B -ntp "$@" test > "$OUT_DIR/$label.log" 2>&1
  local code=$?
  set -e
  echo "$label,$code,$((SECONDS-start))" >> "$OUT_DIR/outcomes.csv"
  echo "CASE $label exit $code"
  grep -E 'Tests run:|Tests are excluded|Tests were excluded|ekstazi|BUILD (SUCCESS|FAILURE)' "$OUT_DIR/$label.log" | tail -n 26 || true
}
rm -rf target .ekstazi
printf 'condition,exit,wall_seconds\n' > "$OUT_DIR/outcomes.csv"
run_case baseline -Pekstazi
run_case nochange -Pekstazi
python3 - <<'PY'
from pathlib import Path
p=Path('src/main/java/lab/ExpiryGate.java')
s=p.read_text()
assert s.count('return (now - issued) <= maxAge;')==1
p.write_text(s.replace('return (now - issued) <= maxAge;', 'return (now - issued) <= maxAge + 10;'))
PY
run_case ordinary_regression -Pekstazi
run_case full_regression
python3 - <<'PY'
import csv
from pathlib import Path
p=Path(__import__('os').environ['EKSTAZI_OUT']) / 'outcomes.csv'
rows={r['condition']: int(r['exit']) for r in csv.DictReader(p.open())}
assert rows['baseline']==0, rows
assert rows['nochange']==0, rows
assert rows['ordinary_regression']!=0, rows
assert rows['full_regression']!=0, rows
print('VERIFIED_EKSTAZI_NATIVE_ORDINARY_DETECTION',rows)
PY
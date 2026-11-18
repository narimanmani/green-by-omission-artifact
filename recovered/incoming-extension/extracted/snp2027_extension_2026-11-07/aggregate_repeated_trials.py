"""Summarize independently recorded native-plugin and full-suite logs.

This script does not manufacture or rerun missing trials. It fails if any of
nine independently recorded trials is absent or violates the expected result.
"""
from pathlib import Path
import csv
import json
import re
from run_protected_ci import ROOT, OUT, CASES, h

ROWS = []
for seed in (0, 1, 42):
    for case, (source_path, security_test) in CASES.items():
        folder = OUT / 'logs' / 'single_repeats' / f'seed_{seed}' / case
        records = {}
        for phase in ('baseline', 'native', 'full'):
            p = folder / f'{phase}.log'
            text = p.read_text()
            exits = re.findall(r'^EXIT:\s*(-?\d+)\s*$', text, flags=re.M)
            counts = re.findall(r'collected\s+(\d+)\s+items?', text)
            secs = re.findall(r'^SECONDS:\s*([\d.]+)\s*$', text, flags=re.M)
            assert len(exits) == 1 and len(counts) >= 1 and len(secs) == 1, str(p)
            records[phase] = {'exit': int(exits[0]), 'collected':int(counts[-1]),'seconds': float(secs[0]), 'log':str(p.relative_to(ROOT)), 'security_test_present': security_test in text}
        main_db = OUT / 'trusted_main_artifacts' / case / f'seed_{seed}' / 'baseline.db'
        assert main_db.exists(), str(main_db)
        checks = {
            'baseline_pass': records['baseline']['exit'] == 0,
            'baseline_collected_security_tests': records['baseline']['collected'] == 3,
            'native_check_passes': records['native']['exit'] == 0,
            'native_collected_zero': records['native']['collected'] == 0,
            'full_suite_fails': records['full']['exit'] == 1,
            'full_collected_three': records['full']['collected'] == 3,
            'full_security_test_detects_regression': records['full']['security_test_present'],
            'trusted_main_baseline_exists': main_db.exists(),
        }
        ROWS.append({'seed':seed,'case':case,'app_source':source_path,
           'baseline_exit': records['baseline']['exit'], 'baseline_collected': records['baseline']['collected'],
           'native_exit': records['native']['exit'], 'native_collected': records['native']['collected'],
           'full_exit': records['full']['exit'], 'full_collected': records['full']['collected'],
           'native_seconds': records['native']['seconds'], 'full_seconds': records['full']['seconds'],
           'trusted_baseline_sha256': h(main_db),
           'native_log':records['native']['log'],'full_log':records['full']['log'],
           'all_checks': all(checks.values()), 'checks':json.dumps(checks,sort_keys=True)})
out_csv=OUT/'single_file_repeats.csv'
with out_csv.open('w',newline='') as fp:
  writer=csv.DictWriter(fp,fieldnames=ROWS[0].keys());writer.writeheader();writer.writerows(ROWS)
(OUT/'single_file_repeats.json').write_text(json.dumps(ROWS,indent=2))
assert len(ROWS) == 9, len(ROWS)
assert all(row['all_checks'] for row in ROWS), [row for row in ROWS if not row['all_checks']]
print('VERIFIED',len(ROWS),'native plugin trials, clean trusted DB and full-suite control, all assertions passed')
for row in ROWS: print(row['seed'],row['case'],row['native_exit'],row['native_collected'],row['full_exit'],row['full_collected'],row['all_checks'])

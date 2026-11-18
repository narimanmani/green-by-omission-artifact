"""Analyze two already-recorded public source snapshots; execute neither subject."""
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path

from testmon.process_code import Module, match_fingerprint, methods_to_checksums


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    case = json.loads(Path('/opt/diagnosis/saved-case.json').read_text())
    baseline, candidate = case['baseline_source'], case['candidate_source']
    assert sha(baseline.encode()) == case['baseline_sha256']
    assert sha(candidate.encode()) == case['candidate_sha256']
    modules = [Module(source_code=s, filename='src/requests/utils.py') for s in [baseline, candidate]]
    blocks = [[b for b in m.blocks if b.name == 'get_netrc_auth'] for m in modules]
    assert all(len(b) == 1 for b in blocks)
    old, new = blocks[0][0], blocks[1][0]
    fingerprints = [methods_to_checksums([b.checksum])[0] for b in [old, new]]
    original_tests = ast.parse(case['original_tests'])
    test_class = next(n for n in original_tests.body if isinstance(n, ast.ClassDef) and n.name == 'TestGetNetrcAuth')
    direct_calls = [n.name for n in test_class.body if isinstance(n, ast.FunctionDef) and any(isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id == 'get_netrc_auth' for x in ast.walk(n))]
    result = {
        'status': 'CONFIRMED_ORDINARY_CHANGE_DETECTED',
        'method': 'Native published testmon representation and matching on two saved snapshots; subject code and tests are not executed',
        'testmon_version': importlib.metadata.version('pytest-testmon'),
        'uid': os.getuid(),
        'interfaces': sorted(p.name for p in Path('/sys/class/net').iterdir()),
        'baseline_source_sha256': case['baseline_sha256'],
        'candidate_source_sha256': case['candidate_sha256'],
        'original_tests_sha256': sha(case['original_tests'].encode()),
        'function': 'get_netrc_auth',
        'native_representation_equal': old.checksum == new.checksum,
        'native_function_crc32_equal': fingerprints[0] == fingerprints[1],
        'baseline_function_crc32': fingerprints[0],
        'candidate_function_crc32': fingerprints[1],
        'baseline_function_fingerprint_matches_baseline': match_fingerprint(modules[0], [fingerprints[0]]),
        'baseline_function_fingerprint_matches_candidate': match_fingerprint(modules[1], [fingerprints[0]]),
        'original_tests_directly_calling_changed_function': sorted(direct_calls),
        'recorded_selective_actual_calls': case['recorded_selective_calls'],
        'new_candidate_or_variant_generated': False,
        'selection_configuration_modified': False,
        'scope_limit': 'This is a static native-fingerprint check joined to prior executed-call records; no post-exit temporary baseline database is reconstructed or claimed independently rehashed.'
    }
    assert result['uid'] == 10001 and result['interfaces'] == ['lo']
    assert result['baseline_function_fingerprint_matches_baseline']
    assert not result['baseline_function_fingerprint_matches_candidate']
    assert not result['native_representation_equal'] and not result['native_function_crc32_equal']
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

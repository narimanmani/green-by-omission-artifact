"""Regression tests for the protected fixture gate; candidate code never runs."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from research_20261107.fixture_policy import (
    POLICY_PATH, TARGET_PATH, build_fixture, validate_candidate,
)

SOURCE_ROOT = Path(__file__).resolve().parents[1]


def git(repo: Path, *arguments: str, data: bytes | None = None) -> bytes:
    env = os.environ.copy()
    env.update(GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0')
    return subprocess.run(
        ['git', '--no-replace-objects', '-c', 'core.fsmonitor=false', *arguments],
        cwd=repo, env=env, input=data, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=True, timeout=30).stdout


def write(repo: Path, relative: str, content: bytes) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def commit(repo: Path, *, stage: bool = True, empty: bool = False) -> str:
    if stage:
        git(repo, 'add', '--all')
    arguments = ['commit', '--no-verify', '-q', '-m', 'temporary regression fixture']
    if empty:
        arguments.append('--allow-empty')
    git(repo, *arguments)
    return git(repo, 'rev-parse', 'HEAD').decode('ascii').strip()


class FixturePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original = git(SOURCE_ROOT, 'show', 'HEAD:' + TARGET_PATH)
        cls.policy_bytes = (SOURCE_ROOT / POLICY_PATH).read_bytes()

    def setUp(self) -> None:
        # Keep all synthetic repositories inside this already-disposable task.
        self.temp = tempfile.TemporaryDirectory(prefix='fixture-policy-', dir=SOURCE_ROOT.parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / 'trusted'
        self.base.mkdir()
        git(self.base, 'init', '-q')
        git(self.base, 'config', 'user.name', 'Fixture Policy Regression')
        git(self.base, 'config', 'user.email', 'fixture-policy@example.invalid')
        git(self.base, 'config', 'commit.gpgsign', 'false')
        git(self.base, 'config', 'core.autocrlf', 'false')
        git(self.base, 'config', 'core.filemode', 'true')
        write(self.base, '.gitattributes', b'* -text\n')
        write(self.base, TARGET_PATH, self.original)
        write(self.base, POLICY_PATH, self.policy_bytes)
        write(self.base, 'cases/requests_crlf_header/tests/test_security.py', b'# trusted test\n')
        write(self.base, '.github/workflows/validation.yml', b'# trusted workflow\n')
        self.base_sha = commit(self.base)
        self.candidate = self.root / 'candidate'
        git(self.root, 'clone', '--quiet', '--no-hardlinks', str(self.base), str(self.candidate))
        for key, value in (('user.name', 'Fixture Policy Regression'),
                           ('user.email', 'fixture-policy@example.invalid'),
                           ('commit.gpgsign', 'false'), ('core.autocrlf', 'false')):
            git(self.candidate, 'config', key, value)
        self.policy = self.base / POLICY_PATH
        self.fixture = build_fixture(self.original, self.policy)

    def approve(self) -> str:
        write(self.candidate, TARGET_PATH, self.fixture)
        return commit(self.candidate)

    def validate(self, selected_head: str, **overrides) -> bytes:
        arguments = dict(base_repo=self.base, candidate_repo=self.candidate,
                         base_sha=self.base_sha, head_sha=selected_head,
                         original=self.original, policy_path=self.policy)
        arguments.update(overrides)
        return validate_candidate(**arguments)

    def test_constructed_fixture_has_independently_reviewed_digest(self) -> None:
        self.assertEqual(hashlib.sha256(self.original).hexdigest(),
                         '5aa53ceab677c2f842fad42359c8ed1ff1c4299c1607789609957a496e4311d4')
        self.assertEqual(len(self.fixture), 33270)
        self.assertEqual(hashlib.sha256(self.fixture).hexdigest(),
                         '0d73a268f74ffd673056d818fae5ee42eab45758ccc81fa041cbe326b887771f')

    def test_exact_fixture_in_single_direct_child_is_accepted(self) -> None:
        self.assertEqual(self.validate(self.approve()), self.fixture)
        self.assertEqual((self.base / TARGET_PATH).read_bytes(), self.original)

    def test_unknown_baseline_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, 'unreviewed baseline'):
            build_fixture(self.original + b'\n# unknown source\n', self.policy)

    def test_unknown_candidate_source_is_rejected(self) -> None:
        write(self.candidate, TARGET_PATH, self.original + b'\n# unknown change\n')
        with self.assertRaisesRegex(RuntimeError, 'exact reviewed fixture'):
            self.validate(commit(self.candidate))

    def test_malicious_evidence_writer_suffix_is_rejected_without_execution(self) -> None:
        marker = self.root / 'forged-evidence.json'
        malicious = ("\nfrom pathlib import Path\nPath(" + repr(str(marker))
                     + ").write_text('forged evidence')\n").encode('utf-8')
        write(self.candidate, TARGET_PATH, self.fixture + malicious)
        with self.assertRaisesRegex(RuntimeError, 'exact reviewed fixture'):
            self.validate(commit(self.candidate))
        self.assertFalse(marker.exists())

    def test_extra_tests_workflow_and_policy_changes_are_rejected(self) -> None:
        for relative in ('cases/requests_crlf_header/tests/test_security.py',
                         '.github/workflows/validation.yml', POLICY_PATH):
            with self.subTest(relative=relative):
                git(self.candidate, 'reset', '--hard', self.base_sha)
                write(self.candidate, TARGET_PATH, self.fixture)
                write(self.candidate, relative, b'# candidate-controlled override\n')
                with self.assertRaisesRegex(RuntimeError, 'only the reviewed target'):
                    self.validate(commit(self.candidate))

    def test_candidate_executable_mode_is_rejected(self) -> None:
        write(self.candidate, TARGET_PATH, self.fixture)
        git(self.candidate, 'add', '--all')
        git(self.candidate, 'update-index', '--chmod=+x', TARGET_PATH)
        with self.assertRaisesRegex(RuntimeError, '100644'):
            self.validate(commit(self.candidate, stage=False))

    def test_candidate_symlink_git_mode_is_rejected(self) -> None:
        # Stage a symlink object directly; no OS symlink privilege is necessary.
        oid = git(self.candidate, 'hash-object', '-w', '--stdin', data=self.fixture).strip()
        git(self.candidate, 'update-index', '--cacheinfo',
            '120000,' + oid.decode('ascii') + ',' + TARGET_PATH)
        with self.assertRaisesRegex(RuntimeError, 'only the reviewed target|100644'):
            self.validate(commit(self.candidate, stage=False))

    def test_nonregular_base_blob_is_rejected(self) -> None:
        for mode in ('100755', '120000'):
            with self.subTest(mode=mode):
                git(self.base, 'reset', '--hard', self.base_sha)
                oid = git(self.base, 'hash-object', '-w', '--stdin', data=self.original).strip()
                git(self.base, 'update-index', '--cacheinfo',
                    mode + ',' + oid.decode('ascii') + ',' + TARGET_PATH)
                mode_base = commit(self.base, stage=False)
                git(self.candidate, 'fetch', '--quiet', str(self.base), mode_base)
                git(self.candidate, 'reset', '--hard', mode_base)
                # Install the fixture as a regular blob without following links.
                fixture_oid = git(self.candidate, 'hash-object', '-w', '--stdin',
                                  data=self.fixture).strip()
                git(self.candidate, 'update-index', '--cacheinfo',
                    '100644,' + fixture_oid.decode('ascii') + ',' + TARGET_PATH)
                head = commit(self.candidate, stage=False)
                with self.assertRaisesRegex(RuntimeError, 'only the reviewed target|100644'):
                    self.validate(head, base_sha=mode_base)

    def test_extra_commit_with_same_final_fixture_is_rejected(self) -> None:
        self.approve()
        head = commit(self.candidate, empty=True)
        with self.assertRaisesRegex(RuntimeError, 'one direct-parent commit'):
            self.validate(head)

    def test_merge_commit_with_same_final_fixture_is_rejected(self) -> None:
        approved = self.approve()
        tree = git(self.candidate, 'rev-parse', approved + '^{tree}').decode('ascii').strip()
        merge = git(self.candidate, 'commit-tree', tree, '-p', self.base_sha, '-p', approved,
                    data=b'temporary merge fixture\n').decode('ascii').strip()
        git(self.candidate, 'reset', '--hard', merge)
        with self.assertRaisesRegex(RuntimeError, 'one direct-parent commit'):
            self.validate(merge)

    def test_wrong_base_sha_is_rejected(self) -> None:
        head = self.approve()
        with self.assertRaisesRegex(RuntimeError, 'does not match BASE'):
            self.validate(head, base_sha='0' * 40)

    def test_candidate_based_on_other_commit_is_rejected(self) -> None:
        other_base = commit(self.candidate, empty=True)
        self.assertNotEqual(other_base, self.base_sha)
        with self.assertRaisesRegex(RuntimeError, 'one direct-parent commit'):
            self.validate(self.approve())

    def test_wrong_head_sha_is_rejected(self) -> None:
        self.approve()
        with self.assertRaisesRegex(RuntimeError, 'does not match HEAD'):
            self.validate(self.base_sha)

    def test_non_full_or_option_like_shas_are_rejected(self) -> None:
        head = self.approve()
        for bad in ('HEAD', head[:12], '--help', 'g' * 40, head + '\n'):
            for parameter in ('base_sha', 'head_sha'):
                with self.subTest(value=bad, parameter=parameter):
                    with self.assertRaisesRegex(RuntimeError, '40-hex'):
                        self.validate(head, **{parameter: bad})

    def test_uncommitted_candidate_worktree_cannot_change_selected_git_blob(self) -> None:
        head = self.approve()
        marker = self.root / 'worktree-evidence.json'
        source = ("from pathlib import Path\nPath(" + repr(str(marker))
                  + ").write_text('forged evidence')\n").encode('utf-8')
        write(self.candidate, TARGET_PATH, source)
        write(self.candidate, POLICY_PATH, b'invalid candidate policy; never read')
        returned = self.validate(head)
        self.assertEqual(returned, self.fixture)
        self.assertNotEqual(returned, (self.candidate / TARGET_PATH).read_bytes())
        self.assertFalse(marker.exists())
        (self.candidate / TARGET_PATH).unlink()
        self.assertEqual(self.validate(head), self.fixture)

    def test_candidate_policy_is_rejected_before_it_can_be_read(self) -> None:
        head = self.approve()
        write(self.candidate, POLICY_PATH, b'invalid JSON')
        with self.assertRaisesRegex(RuntimeError, 'protected base checkout'):
            self.validate(head, policy_path=self.candidate / POLICY_PATH)

    def test_no_target_change_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, 'only the reviewed target'):
            self.validate(commit(self.candidate, empty=True))

    def test_renamed_target_is_rejected(self) -> None:
        git(self.candidate, 'mv', TARGET_PATH, TARGET_PATH + '.renamed')
        with self.assertRaisesRegex(RuntimeError, 'only the reviewed target'):
            self.validate(commit(self.candidate))

    def test_trusted_git_blob_must_match_original(self) -> None:
        head = self.approve()
        with self.assertRaisesRegex(RuntimeError, 'baseline Git blob mismatch'):
            self.validate(head, original=self.original + b'\n')

    def test_policy_must_produce_the_pinned_digest(self) -> None:
        policy = json.loads(self.policy_bytes)
        policy['replacements'][0]['new'] += '# unreviewed\n'
        self.policy.write_text(json.dumps(policy), encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'fixture digest mismatch'):
            build_fixture(self.original, self.policy)

    def test_policy_literals_must_be_unique(self) -> None:
        policy = json.loads(self.policy_bytes)
        policy['replacements'][0]['old'] = '    '
        self.policy.write_text(json.dumps(policy), encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'not unique'):
            build_fixture(self.original, self.policy)

    def test_git_command_failure_is_runtime_error(self) -> None:
        head = self.approve()
        with self.assertRaisesRegex(RuntimeError, 'Git validation failed'):
            self.validate(head, candidate_repo=self.root / 'missing-repository')


if __name__ == '__main__':
    unittest.main()

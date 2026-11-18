"""Protected-base-owned construction and admission of one reviewed fixture.

Candidate Python is never imported, parsed, or executed here. Admission inspects
committed Git objects, and returns independently constructed trusted bytes.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

TARGET_PATH = 'cases/requests_crlf_header/requests/utils.py'
POLICY_PATH = 'research_20261107/reviewed_fixture.json'


def must(ok: bool, reason: str) -> None:
    if not ok:
        raise RuntimeError(reason)


def build_fixture(original: bytes, policy_path: Path) -> bytes:
    """Construct approved bytes using a policy supplied by the trusted base.

    Callers must select protected-base policy. validate_candidate additionally
    enforces its location before calling this function.
    """
    try:
        policy = json.loads(policy_path.read_bytes())
        must(isinstance(policy, dict) and set(policy) == {
            'version', 'target', 'baseline_sha256', 'fixture_sha256', 'replacements'
        }, 'invalid reviewed-fixture policy fields')
        must(type(policy['version']) is int and policy['version'] == 1,
             'unsupported reviewed-fixture policy version')
        must(policy['target'] == TARGET_PATH, 'unexpected reviewed-fixture target')
        for name in ('baseline_sha256', 'fixture_sha256'):
            must(isinstance(policy[name], str)
                 and re.fullmatch(r'[0-9a-f]{64}', policy[name]) is not None,
                 'invalid reviewed-fixture digest: ' + name)
        must(hashlib.sha256(original).hexdigest() == policy['baseline_sha256'],
             'unreviewed baseline source')
        replacements = policy['replacements']
        must(isinstance(replacements, list) and len(replacements) == 3,
             'expected exactly three reviewed literal replacements')
        fixture = original
        for replacement in replacements:
            must(isinstance(replacement, dict) and set(replacement) == {'old', 'new'},
                 'invalid reviewed literal replacement')
            must(all(isinstance(replacement[key], str) for key in ('old', 'new')),
                 'reviewed literals must be strings')
            old, new = replacement['old'].encode('utf-8'), replacement['new'].encode('utf-8')
            must(bool(old) and old != new and original.count(old) == 1
                 and fixture.count(old) == 1, 'reviewed literal is not unique')
            fixture = fixture.replace(old, new, 1)
        must(hashlib.sha256(fixture).hexdigest() == policy['fixture_sha256'],
             'constructed fixture digest mismatch')
        return fixture
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as error:
        raise RuntimeError('cannot construct reviewed fixture: ' + str(error)) from error


def _git(repo: Path, *arguments: str) -> bytes:
    env = os.environ.copy()
    # Ignore replacement objects and forbid on-demand network object retrieval.
    env.update(GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0')
    try:
        result = subprocess.run(
            ['git', '--no-replace-objects', '--literal-pathspecs', '-c',
             'core.fsmonitor=false', *arguments], cwd=repo, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=30)
        return result.stdout
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError('Git validation failed: ' + ' '.join(arguments[:2])) from error


def _blob(repo: Path, revision: str) -> bytes:
    entry = _git(repo, 'ls-tree', '-z', revision, '--', TARGET_PATH)
    match = re.fullmatch(
        rb'100644 blob ([0-9a-f]{40})\t' + re.escape(TARGET_PATH.encode('ascii')) + rb'\x00',
        entry)
    must(match is not None, 'target must be exactly one regular 100644 Git blob')
    return _git(repo, 'cat-file', 'blob', match.group(1).decode('ascii'))


def validate_candidate(base_repo: Path, candidate_repo: Path, base_sha: str,
                       head_sha: str, original: bytes, policy_path: Path) -> bytes:
    """Admit only the exact fixture in one source-only direct child of BASE.

    HEAD selects committed blobs. Uncommitted candidate worktree content is not
    inspected or returned, including any candidate copy of the policy.
    """
    for revision in (base_sha, head_sha):
        must(isinstance(revision, str) and re.fullmatch(r'[0-9a-fA-F]{40}', revision)
             is not None, 'expected a full 40-hex Git commit SHA')
    base_sha, head_sha = base_sha.lower(), head_sha.lower()
    base_repo, candidate_repo = base_repo.resolve(), candidate_repo.resolve()
    must(base_repo != candidate_repo, 'trusted and candidate checkouts must differ')
    policy_path = policy_path.resolve()
    must(policy_path == base_repo / POLICY_PATH
         and not policy_path.is_relative_to(candidate_repo),
         'fixture policy must come from the protected base checkout')
    must(_git(base_repo, 'rev-parse', '--verify', 'HEAD').strip() == base_sha.encode('ascii'),
         'trusted checkout does not match BASE')
    must(_git(candidate_repo, 'rev-parse', '--verify', 'HEAD').strip()
         == head_sha.encode('ascii'), 'candidate checkout does not match HEAD')
    parents = _git(candidate_repo, 'rev-list', '--parents', '-n', '1', head_sha).split()
    must(parents == [head_sha.encode('ascii'), base_sha.encode('ascii')],
         'candidate must be one direct-parent commit on BASE')
    changed = _git(candidate_repo, 'diff', '--no-ext-diff', '--no-textconv',
                   '--name-status', '--no-renames', base_sha, head_sha, '--')
    must(changed == ('M\t' + TARGET_PATH + '\n').encode('ascii'),
         'candidate may modify only the reviewed target source')
    must(_blob(base_repo, base_sha) == original, 'trusted baseline Git blob mismatch')
    candidate = _blob(candidate_repo, head_sha)
    fixture = build_fixture(original, policy_path)
    must(hashlib.sha256(candidate).digest() == hashlib.sha256(fixture).digest()
         and candidate == fixture, 'candidate Git blob is not the exact reviewed fixture')
    return fixture

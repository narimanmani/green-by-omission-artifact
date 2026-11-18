"""Exercise the exact workflow reporter with mocked HTTP; no GitHub writes."""
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import textwrap
import unittest
from unittest.mock import patch
import urllib.request

WORKFLOW = Path(__file__).resolve().parents[1] / '.github/workflows/validation.yml'
TEXT = WORKFLOW.read_text(encoding='utf-8')
REPORTER = textwrap.dedent(TEXT.split("          python - <<'PY'\n", 1)[1]
                          .split("          PY\n", 1)[0])
HEAD, BASE = 'a' * 40, 'b' * 40
REPO = 'anonymous-owner/ci-selection-testbed'


class ReporterTests(unittest.TestCase):
    def exercise(self, result='success', current_change=None, event_change=None):
        event = {'number': 99, 'repository': {'private': True}, 'pull_request': {
            'head': {'sha': HEAD, 'repo': {'full_name': REPO}},
            'base': {'sha': BASE, 'ref': 'main'}}}
        if event_change:
            event_change(event)
        current = copy.deepcopy(event['pull_request'])
        current['state'] = 'open'
        if current_change:
            current_change(current)
        requests = []

        def http(req, timeout):
            self.assertEqual(timeout, 30)
            requests.append(req)
            return io.BytesIO(json.dumps(current if req.data is None else {}).encode())

        with tempfile.TemporaryDirectory(dir=os.environ.get('SP2027_TEST_TMP')) as temporary:
            event_path = Path(temporary) / 'event.json'
            event_path.write_text(json.dumps(event), encoding='utf-8')
            env = {'GITHUB_EVENT_PATH': str(event_path), 'GITHUB_REPOSITORY': REPO,
                   'GITHUB_SHA': BASE, 'GITHUB_API_URL': 'https://api.github.com',
                   'GITHUB_SERVER_URL': 'https://github.com', 'GITHUB_RUN_ID': '123',
                   'GH_TOKEN': 'test-only-token', 'SELECTION_RESULT': result}
            with patch.dict(os.environ, env), patch.object(urllib.request, 'urlopen', http):
                try:
                    exec(compile(REPORTER, str(WORKFLOW), 'exec'), {})
                except SystemExit as error:
                    self.assertEqual(error.code, 0)
        return requests

    def test_success_posts_only_to_exact_head(self):
        requests = self.exercise()
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[1].full_url,
                         'https://api.github.com/repos/' + REPO + '/statuses/' + HEAD)
        body = json.loads(requests[1].data)
        self.assertEqual(body['state'], 'success')
        self.assertEqual(body['context'], 'testmon-required')

    def test_failed_cancelled_skipped_or_unknown_selection_never_succeeds(self):
        for result in ('failure', 'cancelled', 'skipped', '', 'SUCCESS'):
            with self.subTest(result=result):
                requests = self.exercise(result)
                self.assertEqual(json.loads(requests[1].data)['state'], 'failure')

    def test_stale_head_does_not_post(self):
        self.assertEqual(len(self.exercise(current_change=lambda p: p['head'].update(sha='c'*40))), 1)

    def test_stale_base_does_not_post(self):
        self.assertEqual(len(self.exercise(current_change=lambda p: p['base'].update(sha='c'*40))), 1)

    def test_closed_pr_does_not_post(self):
        self.assertEqual(len(self.exercise(current_change=lambda p: p.update(state='closed'))), 1)

    def test_nonmain_current_base_does_not_post(self):
        self.assertEqual(len(self.exercise(current_change=lambda p: p['base'].update(ref='other'))), 1)

    def test_fork_event_is_rejected(self):
        with self.assertRaises(AssertionError):
            self.exercise(event_change=lambda e: e['pull_request']['head']['repo'].update(full_name='evil/fork'))

    def test_base_must_equal_workflow_default_sha(self):
        with self.assertRaises(AssertionError):
            self.exercise(event_change=lambda e: e['pull_request']['base'].update(sha='c'*40))

    def test_invalid_sha_is_rejected(self):
        with self.assertRaises(AssertionError):
            self.exercise(event_change=lambda e: e['pull_request']['head'].update(sha='../bad'))


if __name__ == '__main__':
    unittest.main()


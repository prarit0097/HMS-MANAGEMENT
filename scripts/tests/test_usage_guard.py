"""Owner's usage-stop/cooldown behaviour, tested through the CLI boundary."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'usage_guard.py'


class UsageGuardTests(unittest.TestCase):
    def run_guard(self, usage, state=None, now='2026-10-23T10:00:00+00:00'):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / 'state.json'
            if state:
                state_path.write_text(json.dumps(state), encoding='utf-8')
            result = subprocess.run(
                [sys.executable, str(SCRIPT), '--state', str(state_path), '--now', now],
                input=json.dumps(usage), text=True, capture_output=True, check=False,
            )
            return result, json.loads(result.stdout) if result.stdout else None

    @staticmethod
    def usage(primary=34, secondary=35):
        return {'rateLimitsByLimitId': {'codex': {
            'primary': {'usedPercent': primary}, 'secondary': {'usedPercent': secondary},
        }}}

    def test_recovered_windows_allow_work(self):
        process, result = self.run_guard(self.usage())
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(result['action'], 'continue')
        self.assertEqual(result['minimum_remaining_percent'], 65)

    def test_exact_ten_percent_stops_and_sets_330_minute_deadline(self):
        process, result = self.run_guard(self.usage(90))
        self.assertEqual(process.returncode, 75, process.stderr)
        self.assertEqual(result['action'], 'checkpoint_and_stop')
        self.assertEqual(result['resume_not_before_utc'], '2026-10-23T15:30:00+00:00')

    def test_low_weekly_limit_also_stops(self):
        process, result = self.run_guard(self.usage(10, 95))
        self.assertEqual(process.returncode, 75, process.stderr)
        self.assertEqual(result['minimum_remaining_percent'], 5)

    def test_active_deadline_never_extended_by_repeated_low_reading(self):
        existing = {'checkpoint_at_utc': '2026-10-23T09:00:00+00:00',
                    'resume_not_before_utc': '2026-10-23T14:30:00+00:00'}
        process, result = self.run_guard(self.usage(99), existing)
        self.assertEqual(process.returncode, 75, process.stderr)
        self.assertEqual(result['action'], 'wait_cooldown')
        self.assertEqual(result['resume_not_before_utc'], existing['resume_not_before_utc'])

    def test_recovered_usage_does_not_resume_before_deadline(self):
        existing = {'checkpoint_at_utc': '2026-10-23T09:00:00+00:00',
                    'resume_not_before_utc': '2026-10-23T14:30:00+00:00'}
        process, result = self.run_guard(self.usage(), existing)
        self.assertEqual(process.returncode, 75, process.stderr)
        self.assertEqual(result['action'], 'wait_cooldown')

    def test_after_deadline_and_recovery_resumes(self):
        existing = {'checkpoint_at_utc': '2026-10-23T03:00:00+00:00',
                    'resume_not_before_utc': '2026-10-23T08:30:00+00:00'}
        process, result = self.run_guard(self.usage(), existing)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIsNone(result['resume_not_before_utc'])

    def test_missing_or_nonfinite_usage_never_allows_new_work(self):
        for usage in [{}, self.usage(float('nan')), self.usage(True)]:
            with self.subTest(usage=usage):
                process, result = self.run_guard(usage)
                self.assertEqual(process.returncode, 76, process.stderr)
                self.assertEqual(result['action'], 'usage_unavailable')

    def test_expired_deadline_with_weekly_still_low_stays_stopped(self):
        existing = {'checkpoint_at_utc': '2026-10-23T03:00:00+00:00',
                    'resume_not_before_utc': '2026-10-23T08:30:00+00:00'}
        process, result = self.run_guard(self.usage(20, 98), existing)
        self.assertEqual(process.returncode, 75, process.stderr)
        self.assertEqual(result['action'], 'wait_usage_recovery')
        self.assertEqual(result['resume_not_before_utc'], existing['resume_not_before_utc'])


if __name__ == '__main__':
    unittest.main()

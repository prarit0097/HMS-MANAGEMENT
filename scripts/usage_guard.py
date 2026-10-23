"""Evaluate authenticated usage snapshots without reading credentials.

Feed JSON from Codex get_usage_limits on stdin. Exit 0 allows new work,
75 means checkpoint/wait, and 76 means usage/state cannot be trusted.
Native Codex automation owns scheduling; this script does not call the API.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sys


def timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timezone required')
    return result.astimezone(timezone.utc)


def remaining_percent(usage: dict) -> float:
    buckets = usage.get('rateLimitsByLimitId')
    if not isinstance(buckets, dict) or not buckets:
        legacy = usage.get('rateLimits')
        buckets = {'codex': legacy} if isinstance(legacy, dict) else {}
    remaining = []
    for bucket in buckets.values():
        if not isinstance(bucket, dict):
            raise ValueError('Usage bucket unavailable')
        for name in ('primary', 'secondary'):
            window = bucket.get(name)
            if not isinstance(window, dict):
                raise ValueError('Usage window unavailable')
            used = window.get('usedPercent')
            if isinstance(used, bool) or not isinstance(used, (int, float)):
                raise ValueError('Invalid percentage')
            if not math.isfinite(used) or not 0 <= used <= 100:
                raise ValueError('Invalid percentage')
            remaining.append(100 - used)
    if not remaining:
        raise ValueError('Usage unavailable')
    return min(remaining)


def evaluate(usage: dict, state: dict, now: datetime) -> tuple[dict, int]:
    remaining = remaining_percent(usage)
    deadline_value = state.get('resume_not_before_utc')
    deadline = timestamp(deadline_value) if deadline_value else None
    result = {
        'action': 'continue',
        'minimum_remaining_percent': remaining,
        'checked_at_utc': now.isoformat(),
        'checkpoint_at_utc': state.get('checkpoint_at_utc'),
        'resume_not_before_utc': deadline.isoformat() if deadline else None,
    }
    if deadline and now < deadline:
        result['action'] = 'wait_cooldown'
        return result, 75
    if remaining <= 10:
        if deadline:
            result['action'] = 'wait_usage_recovery'
        else:
            result.update(action='checkpoint_and_stop', checkpoint_at_utc=now.isoformat(),
                          resume_not_before_utc=(now + timedelta(minutes=330)).isoformat())
        return result, 75
    result['checkpoint_at_utc'] = None
    result['resume_not_before_utc'] = None
    return result, 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--now', help='Timezone-aware deterministic test timestamp')
    args = parser.parse_args()
    try:
        now = timestamp(args.now) if args.now else datetime.now(timezone.utc)
        state = json.loads(args.state.read_text(encoding='utf-8')) if args.state.exists() else {}
        if not isinstance(state, dict):
            raise ValueError('Invalid state')
        usage = json.load(sys.stdin)
        if not isinstance(usage, dict):
            raise ValueError('Invalid snapshot')
        result, code = evaluate(usage, state, now)
        args.state.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.state.with_suffix(args.state.suffix + '.tmp')
        temporary.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        temporary.replace(args.state)
    except (ValueError, TypeError, KeyError, OSError):
        result, code = {'action': 'usage_unavailable'}, 76
    print(json.dumps(result, allow_nan=False))
    return code


if __name__ == '__main__':
    raise SystemExit(main())

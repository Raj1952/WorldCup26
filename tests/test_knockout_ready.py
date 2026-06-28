"""
Regression guards: no group-stage-only filters in presentation layer,
and Monte Carlo handles the post-group-stage state (0 remaining group matches).
"""

import os
import re


def test_no_group_stage_filters_in_presentation():
    """No presentation file may filter rows by group-stage labels [A-L]."""
    bad_patterns = [
        r'group_label.*\[A-L\]',
        r'str\.match.*A-L',
        r'GLOB.*\[A-L\]',
        r'No.*group.stage matches',
        r'group-stage matches with known',
    ]
    violations = []
    for root, _dirs, files in os.walk('src/presentation_layer'):
        for fname in files:
            if not fname.endswith('.py'):
                continue
            path = os.path.join(root, fname)
            content = open(path, encoding='utf-8').read()
            for pat in bad_patterns:
                if re.search(pat, content, re.IGNORECASE):
                    violations.append(f'{path}: matches /{pat}/')
    assert not violations, 'Group-stage filters found:\n' + '\n'.join(violations)


def test_monte_carlo_handles_empty_remaining():
    """Sim must not crash when all 72 group matches are played (remaining is empty)."""
    try:
        from src.intelligence_layer.monte_carlo import simulate_full_tournament
        result = simulate_full_tournament(
            'data/tempo.db', 'predictions.parquet', n_sims=500, seed=42
        )
        assert result is not None, 'simulate_full_tournament returned None'
        assert not result.empty, 'simulate_full_tournament returned empty DataFrame'
        assert 'champion_pct' in result.columns, 'champion_pct missing from result'
    except ValueError as exc:
        if 'Columns must be same length' in str(exc):
            raise AssertionError('Empty DataFrame .apply() bug still present') from exc
        raise

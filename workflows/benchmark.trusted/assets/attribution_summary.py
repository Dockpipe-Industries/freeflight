# SPDX-License-Identifier: Apache-2.0
"""Postprocess ordinary controls without discarding any recovery or tail samples."""
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path


def stats(values):
    values = sorted(values)
    assert values
    return {'n': len(values), 'median': statistics.median(values),
            'p90': values[math.ceil(.9 * len(values)) - 1], 'maximum': max(values)}


def summarize(root):
    result = {'postprocessorSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'conditions': [], 'interpretation': 'Ratios above one favor baseline. All steady samples, including recovery, remain included. Pair ranges are descriptive, not confidence intervals. Ordinal does not prove an idle gap.'}
    for mode in ('aa-fixed', 'ab-fixed', 'aa-rotating', 'ab-rotating'):
        receipt = root.with_name(root.name + '-' + mode)
        sessions = json.loads((receipt / 'samples.json').read_text())
        assert json.loads((receipt / 'summary.json').read_text())['status'] == 'passed'
        assert all(not session['diagnostic'] for session in sessions)
        rows = []
        for method in ('symbols', 'definition', 'references', 'workspaceSymbols'):
            pairs = {}
            ordinals = {}
            for session in sessions:
                index = int(session['name'].split('-')[2])
                values = [sample for sample in session['samples']
                          if sample['phase'] == 'steady' and sample['method'] == method]
                variant = session['variant']
                pair = pairs.setdefault(index // 2, {})
                assert variant not in pair
                pair[variant] = {'session': session['name'], **stats([s['ms'] for s in values])}
                for ordinal in sorted({s['ordinal'] for s in values}):
                    ordinals.setdefault((variant, ordinal), []).append(stats(
                        [s['ms'] for s in values if s['ordinal'] == ordinal]))
            paired = []
            for index, pair in sorted(pairs.items()):
                assert set(pair) == {'candidate', 'local-baseline'}
                paired.append({'pair': index, **pair, 'ratios': {
                    stat: pair['candidate'][stat] / pair['local-baseline'][stat]
                    for stat in ('median', 'p90', 'maximum')}})
            rows.append({'method': method, 'pairs': paired, 'ratioSummary': {
                stat: {'median': statistics.median([p['ratios'][stat] for p in paired]),
                       'minimum': min(p['ratios'][stat] for p in paired),
                       'maximum': max(p['ratios'][stat] for p in paired),
                       'candidateLowerPairs': sum(p['ratios'][stat] < 1 for p in paired),
                       'pairs': len(paired)} for stat in ('median', 'p90', 'maximum')},
                'byOrdinal': [{'variant': v, 'ordinal': o, 'sessionStats': data}
                              for (v, o), data in sorted(ordinals.items())]})
        result['conditions'].append({'mode': mode, 'receipt': str(receipt), 'rows': rows})
    (root / 'ordinary-paired-summary.json').write_text(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    summarize(Path(sys.argv[1]).resolve())

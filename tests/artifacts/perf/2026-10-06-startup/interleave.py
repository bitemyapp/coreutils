#!/usr/bin/env python3
"""Randomize short blocks to investigate drift between the initial sweeps."""
import json
import os
from pathlib import Path
import random
import statistics
import subprocess

BASE = Path('/home/callen/work/coreutils-startup-8cf2e4f4')
ART = BASE / 'artifacts'
os.chdir(BASE / 'run')
os.sched_setaffinity(0, {4})
os.environ['LC_ALL'] = 'C'
os.environ['LANG'] = 'C'
cases = json.loads((ART / 'cases.json').read_text())
rng = random.Random(5317)
combined = {name: [] for name in cases}
for block in range(8):
    order = list(cases)
    rng.shuffle(order)
    args = ['hyperfine', '-N', '--warmup', '10', '--runs', '500',
            '--export-json', str(ART / f'interleaved-{block}.json')]
    for name in order:
        args += ['--command-name', name, ' '.join(cases[name])]
    with (ART / f'interleaved-{block}.log').open('w') as out:
        subprocess.run(args, stdout=out, stderr=subprocess.STDOUT, check=True)
    for result in json.loads((ART / f'interleaved-{block}.json').read_text())['results']:
        combined[result['command']] += result['times']
(ART / 'interleaved-times.json').write_text(json.dumps(combined))
for name, values in combined.items():
    print(name, 'mean_us', statistics.mean(values) * 1e6,
          'median_us', statistics.median(values) * 1e6,
          'p95_us', sorted(values)[int(.95 * len(values))] * 1e6)

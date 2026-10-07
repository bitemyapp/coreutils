#!/usr/bin/env python3
"""Warm-cache launch timings, with randomized blocks; run on wx-workstation."""
import json
import os
from pathlib import Path
import random
import shlex
import statistics
import subprocess

ROOT = Path('/home/callen/work/coreutils-startup-factorial')
ART = ROOT / 'artifacts-aggressive'
WORK = ROOT / 'run/bench'
WORK.mkdir(exist_ok=True)
os.chdir(WORK)
os.sched_setaffinity(0, {4})
os.environ.update(LANG='C', LC_ALL='C')
for key in ['LANGUAGE', 'LD_PRELOAD', 'VERSION_CONTROL', 'SIMPLE_BACKUP_SUFFIX']:
    os.environ.pop(key, None)
(WORK / 'src.txt').write_text('startup experiment\n')
CASES = {}
for util in ['true', 'ln']:
    args = [] if util == 'true' else ['-s', '-f', 'src.txt', 'dst.txt']
    CASES[f'gnu-{util}'] = [f'/usr/bin/{util}', *args]
    for variant in ['baseline', 'lazy-musl', 'aggressive-relr', 'aggressive-parser', 'aggressive-crt', 'aggressive']:
        for form in ['single', 'multi']:
            CASES[f'{variant}-{form}-{util}'] = [str(ROOT / 'bin' / variant / form / util), *args]
(ART / 'cases.json').write_text(json.dumps(CASES, indent=2))

def quantile(xs, p):
    xs = sorted(xs)
    position = (len(xs) - 1) * p
    i = int(position)
    return xs[i] + (xs[min(i + 1, len(xs) - 1)] - xs[i]) * (position - i)

def stats(xs):
    return dict(n=len(xs), mean=statistics.mean(xs), p50=quantile(xs, .5),
                p95=quantile(xs, .95), p99=quantile(xs, .99), max=max(xs))

for name, cmd in CASES.items():
    if name.endswith('-ln'):
        (WORK / 'dst.txt').unlink(missing_ok=True)
    for _ in range(2):
        r = subprocess.run(cmd, capture_output=True, check=True)
        assert not r.stdout and not r.stderr, (name, r)
        if name.endswith('-ln'):
            assert os.readlink(WORK / 'dst.txt') == 'src.txt'

all_times = {name: [] for name in CASES}
blocks = []
rng = random.Random(20261006)
for block in range(8):
    order = list(CASES)
    rng.shuffle(order)
    command = ['hyperfine', '-N', '--warmup', '20', '--runs', '1000',
               '--export-json', str(ART / f'timings-{block}.json')]
    for name in order:
        command += ['--command-name', name, shlex.join(CASES[name])]
    with (ART / f'timings-{block}.log').open('w') as out:
        subprocess.run(command, stdout=out, stderr=subprocess.STDOUT, check=True)
    result = json.loads((ART / f'timings-{block}.json').read_text())['results']
    block_stats = {}
    for case in result:
        name = case['command']
        all_times[name].extend(case['times'])
        block_stats[name] = stats(case['times'])
    blocks.append(block_stats)
    print('Completed timing block', block + 1, flush=True)

summary = {name: stats(xs) for name, xs in all_times.items()}
(ART / 'timing-summary.json').write_text(json.dumps(dict(pooled=summary, blocks=blocks), indent=2))
for name, value in summary.items():
    print(f'{name:27s} p50={value["p50"]*1e6:8.2f} p95={value["p95"]*1e6:8.2f} us', flush=True)

# Paired block bootstrap of median latency differences, not individual launches.
differences = {}
for form in ['single', 'multi']:
    for util in ['true', 'ln']:
        for variant in ['baseline', 'lazy-musl', 'aggressive-relr', 'aggressive-parser', 'aggressive-crt', 'aggressive']:
            key = f'{variant}-{form}-{util}'
            ds = [b[key]['p50'] - b[f'gnu-{util}']['p50'] for b in blocks]
            boot = [statistics.mean(rng.choices(ds, k=len(ds))) for _ in range(10000)]
            differences[key] = dict(mean_paired_median_delta_us=statistics.mean(ds)*1e6,
                ci95_us=[quantile(boot, .025)*1e6, quantile(boot, .975)*1e6],
                block_deltas_us=[d*1e6 for d in ds])
(ART / 'paired-differences.json').write_text(json.dumps(differences, indent=2))

# External executable in every iteration; no shell true builtin.
loop = 'for ((i=0; i<5000; i++)); do "$1" || exit; done'
command = ['hyperfine', '-N', '--warmup', '1', '--runs', '8',
           '--export-json', str(ART / 'loops-5000.json')]
for name in ['gnu-true', 'baseline-single-true', 'lazy-musl-single-true',
             'aggressive-crt-single-true', 'aggressive-single-true']:
    command += ['--command-name', name, shlex.join(['/bin/bash', '-c', loop, 'bench', CASES[name][0]])]
with (ART / 'loops-5000.log').open('w') as out:
    subprocess.run(command, stdout=out, stderr=subprocess.STDOUT, check=True)
print('MEASUREMENTS COMPLETE', flush=True)

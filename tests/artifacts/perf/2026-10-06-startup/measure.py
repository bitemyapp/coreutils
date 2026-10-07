#!/usr/bin/env python3
"""Run only on wx-workstation, after the release build finishes."""
import json
import os
from pathlib import Path
import random
import statistics
import subprocess
import time

BASE = Path('/home/callen/work/coreutils-startup-8cf2e4f4')
ART = BASE / 'artifacts'
RUN = BASE / 'run'
os.chdir(RUN)
os.sched_setaffinity(0, {4})
os.environ['LC_ALL'] = 'C'
os.environ['LANG'] = 'C'
os.environ.pop('LANGUAGE', None)
(RUN / 'src.txt').write_text('startup benchmark\n')

CASES = {
    'gnu-true': ['/usr/bin/true'],
    'rust-multi-true': [str(BASE / 'bin/multi/true')],
    'rust-single-true': [str(BASE / 'bin/single/true')],
    'gnu-ln': ['/usr/bin/ln', '-s', '-f', 'src.txt', 'dst.txt'],
    'rust-multi-ln': [str(BASE / 'bin/multi/ln'), '-s', '-f', 'src.txt', 'dst.txt'],
    'rust-single-ln': [str(BASE / 'bin/single/ln'), '-s', '-f', 'src.txt', 'dst.txt'],
}
(ART / 'cases.json').write_text(json.dumps(CASES, indent=2))

def quantiles(values):
    ordered = sorted(values)
    def q(p):
        position = (len(ordered) - 1) * p
        lo = int(position)
        return ordered[lo] + (ordered[min(lo + 1, len(ordered) - 1)] - ordered[lo]) * (position - lo)
    return dict(n=len(values), mean=statistics.mean(values), stdev=statistics.stdev(values),
                p50=q(.5), p95=q(.95), p99=q(.99), p999=q(.999), p9999=q(.9999), max=max(values))

# Verify both first creation and forced replacement, without timing this check.
for name, cmd in CASES.items():
    if name.endswith('-ln'):
        (RUN / 'dst.txt').unlink(missing_ok=True)
    for _ in range(2):
        result = subprocess.run(cmd, capture_output=True, check=True)
        assert result.stdout == b'' and result.stderr == b'', (name, result)
        if name.endswith('-ln'):
            assert os.readlink(RUN / 'dst.txt') == 'src.txt'
(ART / 'smoke-tests.txt').write_text('PASS: all six commands exit 0 with no output; ln creates and replaces the requested symlink.\n')

# Independent forward/reverse sweeps reveal order drift; -N avoids a shell builtin.
summary = {}
for round_number, order in enumerate([list(CASES), list(reversed(CASES))], 1):
    args = ['hyperfine', '-N', '--warmup', '10', '--runs', '2000',
            '--export-json', str(ART / f'hyperfine-{round_number}.json')]
    for name in order:
        args += ['--command-name', name, ' '.join(CASES[name])]
    with (ART / f'hyperfine-{round_number}.log').open('w') as log:
        subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, check=True)
    result = json.loads((ART / f'hyperfine-{round_number}.json').read_text())
    summary[f'round-{round_number}'] = {r['command']: quantiles(r['times']) for r in result['results']}
    print(json.dumps(summary[f'round-{round_number}']), flush=True)

# Explicit external binaries in a Bash loop reproduce the 5,000-launch scenario.
loop = 'for ((i=0; i<5000; i++)); do "$1" || exit; done'
args = ['hyperfine', '-N', '--warmup', '1', '--runs', '20',
        '--export-json', str(ART / 'loops-5000.json')]
import shlex
for name, cmd in CASES.items():
    if name.endswith('-true'):
        args += ['--command-name', name, shlex.join(['/bin/bash', '-c', loop, 'bench', cmd[0]])]
with (ART / 'loops-5000.log').open('w') as log:
    subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, check=True)

# Interleave per-child accounting. Includes fork/exec/wait; not a replacement for hyperfine.
accounting = {name: [] for name in CASES}
order = list(CASES) * 100
random.Random(9041).shuffle(order)
for name in order:
    start = time.perf_counter_ns()
    pid = os.fork()
    if pid == 0:
        os.execv(CASES[name][0], CASES[name])
    _, status, usage = os.wait4(pid, 0)
    assert status == 0, (name, status)
    accounting[name].append(dict(wall_ns=time.perf_counter_ns() - start,
        user_s=usage.ru_utime, sys_s=usage.ru_stime, maxrss_kib=usage.ru_maxrss,
        minor_faults=usage.ru_minflt, major_faults=usage.ru_majflt,
        voluntary_switches=usage.ru_nvcsw, involuntary_switches=usage.ru_nivcsw,
        inblock=usage.ru_inblock, outblock=usage.ru_oublock))
(ART / 'resource-accounting.json').write_text(json.dumps(accounting, indent=2))
(ART / 'summary.json').write_text(json.dumps(summary, indent=2))
print('MEASUREMENTS COMPLETE', flush=True)

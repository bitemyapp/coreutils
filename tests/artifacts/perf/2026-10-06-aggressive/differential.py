#!/usr/bin/env python3
"""Compare the aggressive ln parser and true entry with the previous winner."""
import itertools
import json
import os
from pathlib import Path
import random
import signal
import subprocess
import sys

import golden

ROOT = golden.ROOT
ART = golden.ART
candidate = sys.argv[1] if len(sys.argv) > 1 else 'aggressive'
cases = []
for length in range(4):
    for flags in itertools.product('sfnT', repeat=length):
        short = ['-' + flag for flag in flags]
        cluster = ['-' + ''.join(flags)] if flags else []
        for dst in ['new', 'dst', 'directory', 'directory-link']:
            cases += [short + ['src', dst], ['src', dst] + short,
                      ['src'] + cluster + [dst], cluster + ['--', '-dash', dst]]
# Every ordering of four different flags, which the fast parser accepts.
for flags in itertools.permutations('sfnT'):
    cases.append(['-' + ''.join(flags), 'src', 'dst'])
rng = random.Random(71988)
tokens = ['-s', '-f', '-n', '-T', '-i', '-r', '-P', '-L', '-b', '-v',
          '--sym', '--for', '--backup=numbered', '--suffix=.bak', '--invalid',
          '--help', '--version', '--', '', '-', 'src', 'other', 'dst',
          'new', 'directory', 'directory-link', b'\xff-source']
for _ in range(400):
    cases.append(rng.choices(tokens, k=rng.randrange(0, 9)))
cases = list({tuple(args): args for args in cases}.values())
failures = []
count = 0
for form in ['single', 'multi']:
    for i, args in enumerate(cases):
        # Backup env vars must not enable backups without a backup/suffix option.
        extra = {'VERSION_CONTROL': 'bad', 'SIMPLE_BACKUP_SUFFIX': 'unused'} if i % 3 == 0 else {}
        case = ('ln', args, b'n\n', extra)
        before = golden.run('lazy-musl', form, 'embedded', 'C', case)
        after = golden.run(candidate, form, 'embedded', 'C', case)
        count += 1
        if before != after:
            failures.append(dict(form=form, args=[os.fsdecode(x) for x in args],
                                 env=extra, before=before, after=after))
    print(form, len(cases), 'ln comparisons complete', flush=True)
(ART / 'differential-ln.json').write_text(json.dumps(dict(count=count, failures=failures), indent=2))

# Exercise exact option recognition with arbitrary bytes and multiple operands.
true_cases = [[x] for x in [b'\xff', b'--help\xff', b'', b'--hel', b'--help=',
                           b'--version=', b'--help', b'--version']]
true_cases += [list(xs) for n in [0, 2, 3]
               for xs in itertools.product(['--help', '--version', '', '--', 'operand'], repeat=n)]
true_failures = []
for form in ['single', 'multi']:
    for args in true_cases:
        case = ('true', args, b'', {})
        a = golden.run('lazy-musl', form, 'embedded', 'C', case)
        b = golden.run(candidate, form, 'embedded', 'C', case)
        if a != b:
            true_failures.append(dict(form=form, args=[os.fsdecode(x) for x in args], before=a, after=b))
(ART / 'differential-true.json').write_text(json.dumps(
    dict(count=len(true_cases)*2, failures=true_failures), indent=2))

def fd_case(variant, args, mode, sigpipe):
    env = dict(os.environ, LANG='C', LC_ALL='C')
    env.pop('RUST_SIGPIPE', None)
    if sigpipe:
        env['RUST_SIGPIPE'] = 'default'
    executable = ROOT / 'bin' / variant / 'single/true'
    if mode == 'broken-pipe':
        reader, writer = os.pipe()
        os.close(reader)
        try:
            r = subprocess.run(['true', *args], executable=executable, env=env,
                               stdout=writer, stderr=subprocess.PIPE)
        finally:
            os.close(writer)
    elif mode == 'full':
        with open('/dev/full', 'wb', buffering=0) as out:
            r = subprocess.run(['true', *args], executable=executable, env=env,
                               stdout=out, stderr=subprocess.PIPE)
    else:
        fd = int(mode[-1])
        def close_fd():
            os.close(fd)
        r = subprocess.run(['true', *args], executable=executable, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           preexec_fn=close_fd)
    return dict(code=r.returncode, stdout=(r.stdout or b'').hex(), stderr=(r.stderr or b'').hex())

fd_results = []
for mode, args, sigpipe in itertools.product(
        ['broken-pipe', 'full', 'closed-0', 'closed-1', 'closed-2'],
        [[], ['--help'], ['--version'], ['--help', 'extra']], [False, True]):
    a = fd_case('lazy-musl', args, mode, sigpipe)
    b = fd_case(candidate, args, mode, sigpipe)
    fd_results.append(dict(mode=mode, args=args, sigpipe=sigpipe, before=a, after=b, equal=a==b))
(ART / 'fd-signal-comparison.json').write_text(json.dumps(fd_results, indent=2))
print('ln:', count, 'cases,', len(failures), 'mismatches', flush=True)
print('true:', len(true_cases)*2, 'cases,', len(true_failures), 'mismatches', flush=True)
print('fd/signal:', len(fd_results), 'cases,', sum(not x['equal'] for x in fd_results), 'mismatches', flush=True)
sys.exit(bool(failures or true_failures or any(not x['equal'] for x in fd_results)))

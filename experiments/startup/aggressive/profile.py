#!/usr/bin/env python3
"""Profiles are separate from native timing. Never annotate GNU source."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('/home/callen/work/coreutils-startup-factorial')
ART = ROOT / 'artifacts-aggressive'
os.chdir(ROOT / 'run/bench')
os.sched_setaffinity(0, {4})
os.environ.update(LANG='C', LC_ALL='C')
os.environ.pop('LANGUAGE', None)
VG = Path('/home/callen/work/coreutils-startup-8cf2e4f4/tools/valgrind/usr')
os.environ['VALGRIND_LIB'] = str(VG / 'libexec/valgrind')
cases = json.loads((ART / 'cases.json').read_text())
for name, cmd in cases.items():
    subprocess.run(['strace', '-qq', '-T', '-o', str(ART / f'{name}.strace'), *cmd], check=True)
    subprocess.run(['strace', '-qq', '-c', '-o', str(ART / f'{name}.syscalls'), *cmd], check=True)
    with (ART / f'{name}.time-v.txt').open('w') as out:
        subprocess.run(['/usr/bin/time', '-v', *cmd], stdout=out, stderr=subprocess.STDOUT, check=True)
    with (ART / f'{name}.elf.txt').open('w') as out:
        for tool in [['stat', '-Lc', '%n %s bytes'], ['size'], ['readelf', '-dW'], ['readelf', '-lW']]:
            subprocess.run([*tool, cmd[0]], stdout=out, stderr=subprocess.STDOUT, check=True)
    with (ART / f'{name}.callgrind.log').open('w') as log:
        subprocess.run([str(VG / 'bin/valgrind'), '--tool=callgrind',
            '--callgrind-out-file=' + str(ART / f'{name}.callgrind'), *cmd],
            stdout=log, stderr=subprocess.STDOUT, check=True)
    for inclusive in ['yes', 'no']:
        with (ART / f'{name}.instructions-{inclusive}.txt').open('w') as out:
            subprocess.run([str(VG / 'bin/callgrind_annotate'), '--auto=no',
                '--inclusive=' + inclusive, '--threshold=99', str(ART / f'{name}.callgrind')],
                stdout=out, stderr=subprocess.STDOUT, check=True)
    print(name, 'profiled', flush=True)

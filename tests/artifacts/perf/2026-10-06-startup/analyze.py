#!/usr/bin/env python3
"""Summarize the artifacts on the workstation, without running benchmarks."""
import json
from pathlib import Path
import re
import statistics

ART = Path('/home/callen/work/coreutils-startup-8cf2e4f4/artifacts')

def summarize(values):
    ordered = sorted(values)
    def q(p):
        i = (len(ordered) - 1) * p
        lo = int(i)
        return ordered[lo] + (ordered[min(lo + 1, len(ordered) - 1)] - ordered[lo]) * (i - lo)
    return dict(n=len(values), mean=statistics.mean(values), stdev=statistics.stdev(values),
                p50=q(.5), p95=q(.95), p99=q(.99), p999=q(.999), p9999=q(.9999), max=max(values),
                launches_per_second=1/statistics.mean(values))

out = {'latency_seconds': {}, 'loader_statistics': {}, 'native_stages_us': {}, 'callgrind': {}, 'footprint': {}}
for name, values in json.loads((ART / 'interleaved-times.json').read_text()).items():
    out['latency_seconds'][name] = summarize(values)
    loader = json.loads((ART / f'{name}.loader.json').read_text())
    out['loader_statistics'][name] = {}
    for key in ['total startup time in dynamic loader', 'time needed for relocation',
                'number of relative relocations', 'number of relocations', 'time needed to load objects']:
        values = [int(re.search(re.escape(key) + r':\s+(\d+)', text)[1]) for text in loader]
        out['loader_statistics'][name][key] = statistics.median(values)
    text = (ART / f'{name}.instructions-yes.txt').read_text()
    patterns = {'total': r'PROGRAM TOTALS', 'loader': r':_dl_start ',
                'relocate': r'dl-reloc.c:_dl_relocate_object ',
                'localization': r'locale.rs:uucore::mods::locale::setup_localization ',
                'fluent_parse': r'locale.rs:uucore::mods::locale::parse_fluent_resource_owned ',
                'stack_discovery': r'pthread_getattr_np.c:pthread_getattr_np',
                'ln_uumain': r'ln.rs:uu_ln::uumain ',
                'ln_app': r'ln.rs:uu_ln::uu_app ',
                'clap_parse': r'Command::_do_parse '}
    out['callgrind'][name] = {}
    for key, pattern in patterns.items():
        for line in text.splitlines():
            if re.search(pattern, line):
                out['callgrind'][name][key] = int(line.split()[0].replace(',', ''))
                break
    time_text = (ART / f'{name}.time-v.txt').read_text()
    out['footprint'][name] = {
        key: int(re.search(re.escape(label) + r':\s+(\d+)', time_text)[1])
        for key, label in [('rss_kib', 'Maximum resident set size (kbytes)'),
                           ('minor_faults', 'Minor (reclaiming a frame) page faults'),
                           ('major_faults', 'Major (requiring I/O) page faults'),
                           ('block_inputs', 'File system inputs')]}
for name, records in json.loads((ART / 'native-stages.json').read_text()).items():
    out['native_stages_us'][name] = {
        key.replace('_ns', '_us'): {
            metric: value for metric, value in summarize([r[key] / 1000 for r in records[10:]]).items()
            if metric != 'launches_per_second'
        }
        for key in records[0]}
out['loops_5000_seconds'] = {r['command']: summarize(r['times']) for r in json.loads((ART / 'loops-5000.json').read_text())['results']}
for control in ['strip-control', 'empty-controls']:
    out[control] = {r['command']: summarize(r['times']) for r in json.loads((ART / f'{control}.json').read_text())['results']}
out['block_medians_us'] = {
    str(block): {r['command']: statistics.median(r['times']) * 1e6
                for r in json.loads((ART / f'interleaved-{block}.json').read_text())['results']}
    for block in range(8)}
(ART / 'analysis.json').write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))

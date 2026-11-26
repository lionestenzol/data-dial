"""Reproduce the upstream README's two-program abstraction-learning example."""
import json
from pathlib import Path
from importlib.metadata import version
import stitch_core
programs = ['(foo (a a a))', '(bar (b b b))']
result = stitch_core.compress(programs, iterations=1, max_arity=3)
record = {'version':version('stitch-core'), 'input':programs, 'abstractions':str(result.abstractions), 'rewritten':result.rewritten, 'scope':'Upstream toy example; no held-out utility or runtime improvement measured.'}
assert len(result.abstractions) == 1
assert any('fn_0' in p for p in result.rewritten)
Path(__file__).with_name('stitch_results.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))

from __future__ import annotations
import json, hashlib, random, time, platform
from pathlib import Path
from importlib.metadata import version
from egglog import EGraph, Expr, i64Like, StringLike, rewrite, ruleset, vars_
from egglog.deconstruct import get_callable_args, get_callable_fn, get_literal_value
from redun import task, Scheduler
from redun.config import Config
import wasmtime

class Num(Expr):
    def __init__(self, value: i64Like) -> None: ...
    @classmethod
    def var(cls, name: StringLike) -> Num: ...
    def __add__(self, other: Num) -> Num: ...
    def __mul__(self, other: Num) -> Num: ...

a, = vars_('a', Num)
rules = ruleset(rewrite(a + Num(0)).to(a), rewrite(a * Num(1)).to(a))
x = Num.var('x')
forms = [x + Num(5), (x + Num(0)) * Num(1) + Num(5), (x * Num(1) + Num(5)) + Num(0)]

def lower(expr):
    fn, args = get_callable_fn(expr), get_callable_args(expr)
    if fn == Num: return f'(i64.const {get_literal_value(args[0])})'
    if fn == Num.var:
        assert get_literal_value(args[0]) == 'x'
        return '(local.get 0)'
    op = {Num.__add__: 'i64.add', Num.__mul__: 'i64.mul'}[fn]
    return f'({op} {lower(args[0])} {lower(args[1])})'

def module(expr):
    return f'(module (func (export "f") (param i64) (result i64) {lower(expr)}))'

def normalize(expr):
    graph = EGraph()
    graph.register(expr)
    graph.run(rules * 5)
    return graph.extract(expr)

config = wasmtime.Config()
config.consume_fuel = True
engine = wasmtime.Engine(config)

def guest(wat, value):
    store = wasmtime.Store(engine)
    store.set_fuel(10000)
    instance = wasmtime.Instance(store, wasmtime.Module(engine, wat), [])
    return instance.exports(store)['f'](store, value)

EXECUTIONS = []  # instrumentation only; excluded from semantic result
@task(namespace='riv_smoke', version='1')
def execute(wat: str, value: int):
    EXECUTIONS.append({'module_sha256': hashlib.sha256(wat.encode()).hexdigest(), 'input': value})
    return guest(wat, value)

def scheduler(path):
    instance = Scheduler(config=Config({'backend': {'db_uri': f'sqlite:///{path}'}}))
    instance.load()
    return instance

def run():
    root = Path(__file__).resolve().parent
    paths = [root / 'canonical.db', root / 'baseline.db']
    for path in paths:
        if path.exists(): path.unlink()
    t = time.perf_counter()
    extracted = [normalize(form) for form in forms]
    normal_seconds = time.perf_counter() - t
    canonical_wat = [module(e) for e in extracted]
    assert len(set(canonical_wat)) == 1
    s = scheduler(paths[0])
    outputs = [s.run(execute(w, 7)) for w in canonical_wat]
    assert outputs == [12,12,12]
    first_count = len(EXECUTIONS)
    assert first_count == 1
    changed = s.run(execute(canonical_wat[0], 8))
    assert changed == 13 and len(EXECUTIONS) == 2
    s.backend.session.close()
    fresh = scheduler(paths[0])
    restarted = fresh.run(execute(canonical_wat[0], 7))
    assert restarted == 12 and len(EXECUTIONS) == 2
    before_baseline = len(EXECUTIONS)
    base = scheduler(paths[1])
    baseline = [base.run(execute(module(form),7)) for form in forms]
    baseline_count = len(EXECUTIONS) - before_baseline
    assert baseline == outputs and baseline_count == 3
    rng = random.Random(3214)
    samples = [-(2**63),2**63-1,0,1,-1] + [rng.randrange(-(2**63),2**63) for _ in range(95)]
    checked = 0
    for form, wat in zip(forms, canonical_wat):
        for value in samples:
            expected = (value + 5 + 2**63) % 2**64 - 2**63
            assert guest(wat,value) == guest(module(form),value) == expected
            checked += 1
    result = {'status':'PASS','python':platform.python_version(),'platform':platform.platform(),
              'versions':{p:version(p) for p in ['egglog','redun','wasmtime']},
              'normalized':[str(e) for e in extracted], 'unique_modules':len(set(canonical_wat)),
              'canonical_first_guest_executions':first_count,'changed_input_guest_executions':1,
              'restart_additional_guest_executions':0,'baseline_guest_executions':baseline_count,
              'independent_input_form_checks':checked,'normalization_seconds_single_run':normal_seconds,
              'limitations':['Three identity-rewrite examples only','No upstream full test suites run',
              'No speedup benchmark','Single host only','Rules supplied by experiment author',
              'No synthesis, compressed-query, networking, or capability-learning validation']}
    (root/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__ == '__main__': run()

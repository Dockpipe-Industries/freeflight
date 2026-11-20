# SPDX-License-Identifier: Apache-2.0
"""Reuse the exact MCP oracle; change order/spacing explicitly, never in secret."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import run as trusted

label=os.environ['FREEFLIGHT_POSITION_LABEL']
assert label and all(c.isalnum() or c in '-_' for c in label)
base=trusted.REPO/'bin/.local/glider-comparison'
out=base/label;out.mkdir(exist_ok=False)
fixed=os.environ.get('FREEFLIGHT_POSITION_FIXED_REF','6a06b1d')
fixedReceipt=os.environ.get('FREEFLIGHT_POSITION_FIXED_RECEIPT',str(trusted.REPO/'bin/.local/benchmarks/trusted/shutdown-lifetime-v1'))
config={'fixedRef':trusted.git('rev-parse',fixed),'beforeRef':trusted.git('rev-parse','6636d94'),
        'fixedReceipt':fixedReceipt,'sessions':int(os.environ.get('FREEFLIGHT_POSITION_SESSIONS','2')),
        'rounds':int(os.environ.get('FREEFLIGHT_POSITION_ROUNDS','80')),
        'sourceCommit':trusted.git('rev-parse','HEAD'),
        'driverHashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}}
assert config['sessions']>=2 and config['rounds']>=16 and config['rounds']%8==0
(out/'provenance.json').write_text(json.dumps(config,indent=2))
completed=[]

def run(mode, candidateReceipt, baselineReceipt, baselineRef, prepare=False, diagnostic=False,
        identical=False, order='balanced', gap=0, sizes='5845', intervals='0.1', crossover=False):
    env={**os.environ,'FREEFLIGHT_GLIDER_LABEL':label+'-'+mode,
         'FREEFLIGHT_GLIDER_CANDIDATE_RECEIPT':str(candidateReceipt),
         'FREEFLIGHT_GLIDER_QUALIFIED_WORKER_ONLY':'1',
         'FREEFLIGHT_GLIDER_LOCAL_BASELINE_RECEIPT':str(baselineReceipt),
         'FREEFLIGHT_GLIDER_LOCAL_BASELINE_REF':baselineRef,
         'FREEFLIGHT_GLIDER_CANDIDATE_CORE_REF':'6636d94',
         'FREEFLIGHT_GLIDER_BUILD_CANDIDATE_CORE':'1' if diagnostic or not prepare else '0',
         'FREEFLIGHT_GLIDER_SHARED_WORKER':'1' if identical else '0',
         'FREEFLIGHT_GLIDER_SHARED_CORE':'1' if diagnostic or not prepare else '0',
         'FREEFLIGHT_GLIDER_IDENTICAL_CONTROL':'1' if identical else '0',
         'FREEFLIGHT_GLIDER_PROFILE':'1' if diagnostic else '0',
         'FREEFLIGHT_GLIDER_PREPARE_ONLY':'1' if prepare else '0',
         'FREEFLIGHT_GLIDER_PRODUCTS':'local-baseline,candidate',
         'FREEFLIGHT_GLIDER_QUERY_ORDER':order,'FREEFLIGHT_GLIDER_QUERY_GAP':str(gap),
         'FREEFLIGHT_GLIDER_CADENCE_CROSSOVER':'1' if crossover else '0',
         'FREEFLIGHT_GLIDER_SIZES':sizes,'FREEFLIGHT_GLIDER_INTERVALS':intervals,
         'FREEFLIGHT_GLIDER_SESSIONS':str(config['sessions']),
         'FREEFLIGHT_GLIDER_ROUNDS':str(config['rounds']),'FREEFLIGHT_GLIDER_WARMUP':'10'}
    print('Position condition:',mode,flush=True)
    subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('glider.py'))],env=env,check=True)
    receipt=base/(label+'-'+mode)
    result=json.loads((receipt/('qualification-only.json' if prepare else 'summary.json')).read_text())
    assert result['status']=='passed'
    completed.append({'mode':mode,'receipt':str(receipt),'prepareOnly':prepare})
    (out/'progress.json').write_text(json.dumps(completed,indent=2))
    return receipt

try:
    old=run('before-native',trusted.REPO/'bin/.local/benchmarks/trusted/incremental-v3',
            base/'incremental-v3','6636d94',prepare=True)
    new=run('fixed-native',fixedReceipt,old,'6636d94',prepare=True)
    run('fixed-diagnostic-qualification',fixedReceipt,new,fixed,prepare=True,diagnostic=True,identical=True)
    run('lifetime-balanced',fixedReceipt,old,'6636d94',sizes='433,5845',intervals='0,0.1')
    for mode,order,gap,interval in [('aa-fixed','fixed',0,'0.1'),('aa-balanced','balanced',0,'0.1'),
                                    ('aa-equal-gap','balanced',.02,'0')]:
        run(mode,fixedReceipt,new,fixed,identical=True,order=order,gap=gap,intervals=interval)
    from position_summary import summarize
    summarize(out)
    crossed=run('aa-crossover',fixedReceipt,new,fixed,identical=True,gap=.02,crossover=True)
    from position_summary import summarize_crossover,complete_review
    summarize_crossover(crossed)
    complete_review(out,crossed)
    (out/'summary.json').write_text(json.dumps({'status':'passed','conditions':completed},indent=2))
except Exception as error:
    (out/'failure.json').write_text(json.dumps({'error':repr(error),'completed':completed},indent=2));raise

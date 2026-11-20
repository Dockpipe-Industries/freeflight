# SPDX-License-Identifier: Apache-2.0
"""Serial controlled experiment using the existing product driver and exact oracle."""
import hashlib,json,os,statistics,subprocess,sys
from pathlib import Path
import run as trusted
label=os.environ['FREEFLIGHT_ATTRIBUTION_LABEL']
assert label and all(c.isalnum() or c in '-_' for c in label)
base=trusted.REPO/'bin/.local/glider-comparison'
out=base/label;out.mkdir(exist_ok=False)
modes=os.environ.get('FREEFLIGHT_ATTRIBUTION_MODES','aa-fixed,ab-fixed,aa-rotating,ab-rotating,profile-fixed,profile-rotating').split(',')
allowed={f'{kind}-{order}' for kind in ['aa','ab','profile'] for order in ['fixed','rotating']}
assert set(modes)<=allowed and len(set(modes))==len(modes)
config={'modes':modes,'sessions':int(os.environ.get('FREEFLIGHT_ATTRIBUTION_SESSIONS','4')),'profileSessions':int(os.environ.get('FREEFLIGHT_ATTRIBUTION_PROFILE_SESSIONS','2')),'rounds':int(os.environ.get('FREEFLIGHT_ATTRIBUTION_ROUNDS','80')),
    'sourceCommit':trusted.git('rev-parse','HEAD'),'driverHashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}}
(out/'provenance.json').write_text(json.dumps(config,indent=2))
completed=[]
try:
 for mode in modes:
    kind,order=mode.split('-');runLabel=label+'-'+mode
    env={**os.environ,'FREEFLIGHT_GLIDER_LABEL':runLabel,
      'FREEFLIGHT_GLIDER_CANDIDATE_RECEIPT':str(trusted.REPO/'bin/.local/benchmarks/trusted/incremental-v3'),
      'FREEFLIGHT_GLIDER_LOCAL_BASELINE_RECEIPT':str(base/'incremental-v3'),
      'FREEFLIGHT_GLIDER_LOCAL_BASELINE_REF':'d8232ec','FREEFLIGHT_GLIDER_BUILD_CANDIDATE_CORE':'1',
      'FREEFLIGHT_GLIDER_CANDIDATE_CORE_REF':'d8232ec' if kind=='aa' else '5c44c97',
      'FREEFLIGHT_GLIDER_SHARED_WORKER':'1','FREEFLIGHT_GLIDER_IDENTICAL_CONTROL':'1' if kind=='aa' else '0',
      'FREEFLIGHT_GLIDER_PROFILE':'1' if kind=='profile' else '0',
      'FREEFLIGHT_GLIDER_PRODUCTS':'local-baseline,candidate','FREEFLIGHT_GLIDER_QUERY_ORDER':order,
      'FREEFLIGHT_GLIDER_SIZES':'5845','FREEFLIGHT_GLIDER_INTERVALS':'0.1',
      'FREEFLIGHT_GLIDER_SESSIONS':str(config['profileSessions'] if kind=='profile' else config['sessions']),
      'FREEFLIGHT_GLIDER_ROUNDS':str(config['rounds']),'FREEFLIGHT_GLIDER_WARMUP':'10'}
    env.pop('FREEFLIGHT_GLIDER_PREPARE_ONLY',None)
    print('Attribution condition:',mode,flush=True)
    subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('glider.py'))],env=env,check=True)
    receipt=base/runLabel;result=json.loads((receipt/'summary.json').read_text());assert result['status']=='passed'
    if kind=='profile':
        from native_summary import summarize
        print('Joined native diagnostic samples:',summarize(receipt),flush=True)
    completed.append({'mode':mode,'receipt':str(receipt),'comparisons':result['comparisons']})
    (out/'progress.json').write_text(json.dumps(completed,indent=2))
 ordinaryModes={'aa-fixed','ab-fixed','aa-rotating','ab-rotating'}
 if ordinaryModes <= set(modes):
    from attribution_summary import summarize as summarize_ordinary
    summarize_ordinary(out)
 (out/'summary.json').write_text(json.dumps({'status':'passed','conditions':completed},indent=2))
except Exception as error:
 (out/'failure.json').write_text(json.dumps({'error':repr(error),'completed':completed},indent=2));raise

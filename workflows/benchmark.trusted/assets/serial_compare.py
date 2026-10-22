# SPDX-License-Identifier: Apache-2.0
"""Bounded serial-handle qualification; reuse MCP oracle and separate source profiles."""
import hashlib,json,os,pathlib,subprocess,sys
root=pathlib.Path.cwd();assets=root/'workflows/benchmark.trusted/assets'
label=os.environ.get('FREEFLIGHT_SERIAL_COMPARE_LABEL','serial-recovery-only-repeat')
assert label and all(c.isalnum() or c in '-_' for c in label)
base=root/'bin/.local/glider-comparison';out=base/label
resume=os.environ.get('FREEFLIGHT_SERIAL_COMPARE_RESUME')=='1'
if resume:
 assert list(out.glob('failure*.json')), 'Resume requires a recorded failed orchestration, not an uncertain live run'
 progress=json.loads((out/'progress.json').read_text())
 for row in progress:assert json.loads((pathlib.Path(row['receipt'])/'summary.json').read_text())['status']=='passed'
else:out.mkdir(exist_ok=False);progress=[]
candidate=pathlib.Path(os.environ.get('FREEFLIGHT_SERIAL_CANDIDATE_RECEIPT',str(root/'bin/.local/benchmarks/trusted/serial-handles-v2')))
fixed=pathlib.Path(os.environ.get('FREEFLIGHT_SERIAL_BASELINE_RECEIPT',str(root/'bin/.local/benchmarks/trusted/shutdown-lifetime-v1')))
baseline=pathlib.Path(os.environ.get('FREEFLIGHT_SERIAL_BASELINE_NATIVE_RECEIPT',str(base/'position-lifetime-v2-fixed-native')))
candidateRef=os.environ.get('FREEFLIGHT_SERIAL_CANDIDATE_REF','c3ae753')
proofPath=candidate/'candidate/serial-handle-proof/result.json'
if not proofPath.exists():proofPath=root/'bin/.local/benchmarks/serial-handles/serial-proof-v2/result.json'
proof=json.loads(proofPath.read_text())
frozen=json.loads((candidate/'provenance.json').read_text())['variants']['candidate']['sourceHashes']
assert proof['status']=='passed' and proof['helperSha256']==frozen['workers/roslyn/DarwinSourceHandle.cs'] and proof['programSha256']==frozen['workers/roslyn/Program.cs']
assert 'root symlink cannot fall back:UnauthorizedAccessException' in proof['output'], 'Require the strengthened root-replacement gate before timing'
config=dict(candidateReceipt=str(candidate),candidateRef=candidateRef,baselineReceipt=str(fixed),baselineRef='6a06b1d',rounds=40,warmupSeconds=5,sourceSha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),resumed=resume)
(out/('resume-config.json' if resume else 'config.json')).write_text(json.dumps(config,indent=2)+'\n')
plan=[
 ('balanced',candidate,baseline,'6a06b1d',False,False,'433,5845','0,0.1',2),
 ('identical',fixed,baseline,'6a06b1d',True,False,'5845','0,0.1',2),
 ('small-control',fixed,baseline,'6a06b1d',True,False,'433','0.1',2),
 ('small-repeat',candidate,baseline,'6a06b1d',False,False,'433','0.1',2),
 ('baseline-diagnostic',fixed,baseline,'6a06b1d',True,True,'5845','0',1),
 ('candidate-diagnostic',candidate,base/(label+'-balanced'),candidateRef,True,True,'5845','0',1)]
selected=os.environ.get('FREEFLIGHT_SERIAL_COMPARE_STAGES')
selected=set(selected.split(',')) if selected else {x[0] for x in plan}
assert selected <= {x[0] for x in plan}
for name,receipt,retained,ref,identical,diagnostic,sizes,intervals,sessions in plan:
 if name not in selected:continue
 if any(x['stage']==name for x in progress):continue
 assert not (base/(label+'-'+name)).exists(), 'Existing uncertain/failed condition requires a new label'
 env={**os.environ,'FREEFLIGHT_GLIDER_LABEL':label+'-'+name,
 'FREEFLIGHT_GLIDER_CANDIDATE_RECEIPT':str(receipt),'FREEFLIGHT_GLIDER_QUALIFIED_WORKER_ONLY':'1',
 'FREEFLIGHT_GLIDER_LOCAL_BASELINE_RECEIPT':str(retained),'FREEFLIGHT_GLIDER_LOCAL_BASELINE_REF':ref,
 'FREEFLIGHT_GLIDER_CANDIDATE_CORE_REF':'6a06b1d','FREEFLIGHT_GLIDER_BUILD_CANDIDATE_CORE':'1',
 'FREEFLIGHT_GLIDER_SHARED_CORE':'1','FREEFLIGHT_GLIDER_SHARED_WORKER':'1' if identical else '0',
 'FREEFLIGHT_GLIDER_IDENTICAL_CONTROL':'1' if identical else '0','FREEFLIGHT_GLIDER_PROFILE':'1' if diagnostic else '0',
 'FREEFLIGHT_GLIDER_PRODUCTS':'local-baseline,candidate','FREEFLIGHT_GLIDER_QUERY_ORDER':'balanced',
 'FREEFLIGHT_GLIDER_SIZES':sizes,'FREEFLIGHT_GLIDER_INTERVALS':intervals,
 'FREEFLIGHT_GLIDER_SESSIONS':str(sessions),'FREEFLIGHT_GLIDER_ROUNDS':'40','FREEFLIGHT_GLIDER_WARMUP':'5'}
 print('Serial handle condition:',name,flush=True)
 try:subprocess.run([sys.executable,'-B',str(assets/'glider.py')],env=env,check=True)
 except Exception as e:
  (out/('failure-'+name+'.json')).write_text(json.dumps(dict(stage=name,error=repr(e),completed=progress),indent=2));raise
 result=json.loads((base/(label+'-'+name)/'summary.json').read_text());assert result['status']=='passed'
 progress.append(dict(stage=name,receipt=str(base/(label+'-'+name))))
 (out/'progress.json').write_text(json.dumps(progress,indent=2))
(out/'result.json').write_text(json.dumps(dict(status='passed',resumed=resume,conditions=progress),indent=2))

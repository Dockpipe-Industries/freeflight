# SPDX-License-Identifier: Apache-2.0
"""Narrow all-operation direct-worker screen using the same frozen source/fixtures."""
import hashlib,json,os,shutil,statistics,sys,time
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'workflows/benchmark.trusted/assets'));import run as trusted
receipt=Path.cwd()/'bin/.local/benchmarks/trusted'/(os.environ.get('FREEFLIGHT_OPERATION_RECEIPT') or os.environ['FREEFLIGHT_PATH_RECEIPT']);c=json.loads((receipt/'provenance.json').read_text());label=os.environ.get('FREEFLIGHT_OPERATION_LABEL','all-operations');assert label and all(x.isalnum() or x in '-_' for x in label)
out=receipt/label;out.mkdir(exist_ok=False);trusted.OUT=out;trusted.DOTNET=c['dotnet']
rounds=int(os.environ.get('FREEFLIGHT_OPERATION_ROUNDS','10'));sessions=int(os.environ.get('FREEFLIGHT_OPERATION_SESSIONS','2'));order=os.environ.get('FREEFLIGHT_OPERATION_ORDER','rotating');sizes=os.environ.get('FREEFLIGHT_OPERATION_SIZES','433,5845').split(',')
assert rounds>=10 and sessions>=2 and order in ('rotating','balanced') and set(sizes)<={'433','5845'}
if order=='balanced':assert rounds%12==0
control=os.environ.get('FREEFLIGHT_OPERATION_IDENTICAL','')
assert control in ('','baseline','candidate')
actual={variant:(control or variant) for variant in ('baseline','candidate')}
if control:assert c['baselineArgs']==c['candidateArgs'], 'Identical control requires matching launch flags'
commands={variant:[c['dotnet'],c['variants'][actual[variant]]['dll'],*c[actual[variant]+'Args']] for variant in actual}
for variant in actual:
 entry=c['variants'][actual[variant]]
 assert hashlib.sha256(Path(entry['dll']).read_bytes()).hexdigest()==entry['dllSha256']
if control:assert commands['baseline']==commands['candidate']
(out/'run-manifest.json').write_text(json.dumps(dict(identicalControl=control or None,actualVariants=actual,commands=commands,rounds=rounds,sessions=sessions,order=order,sizes=sizes,adapterSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
shutil.copy2(__file__,out/'adapter-source.py')
rows=[];comparisons=[]
def save(name,data):(out/name).write_text(json.dumps(data,indent=2)+'\n')
for size,frozen in c['fixtures'].items():
 if size not in sizes:continue
 f=dict(frozen);f['root']=str(Path(f['root']).resolve());queries,check=trusted.workload(f,int(size));target=queries[0][1]['file'];position=queries[1][1];line=Path(position['file']).read_text().splitlines()[0]
 queries=queries+[('hover',position),('diagnostics',dict(file=position['file'])),('rename',dict(**position,newName='RenamedValue')),('implementations',position),('typeInfo',position),('signatureHelp',dict(file=position['file'],line=0,character=line.index('.Value(')+len('.Value('))),('callHierarchy',position),('typeHierarchy',dict(file=target,line=0,character=29))]
 expected=None;names={m for m,a in queries};assert len(names)==12
 sequence=[]
 for pair in range(sessions):sequence.extend(['baseline','candidate'] if pair%2==0 else ['candidate','baseline'])
 for index,variant in enumerate(sequence):
  selectedVariant=actual[variant]
  s=trusted.Session(c['variants'][selectedVariant]['dll'],f'{size}-{index}-{variant}',c[selectedVariant+'Args']);row=dict(size=int(size),variant=variant,index=index,samples=[])
  try:
   assert s.call('open',root=f['root'],project=f['project'])[0]['files']==int(size)
   reported=set(s.call('capabilities')[0]['operations']);assert reported==names,(reported,names)
   oracle={}
   for method,args in queries:
    result,_=s.call(method,**args)
    if method in ['symbols','definition','references','workspaceSymbols']:check(method,result)
    oracle[method]=result
   if expected is None:expected=oracle;save(f'{size}-oracle.json',oracle)
   assert oracle==expected,(size,variant,'initial semantic oracle')
   start=time.monotonic();round=0;measured=0
   while time.monotonic()-start<5 or measured<rounds:
    steady=time.monotonic()-start>=5;began=time.monotonic();offset=round%12
    if order=='balanced':
     phase=measured if steady else round
     design=[0,1,11,2,10,3,9,4,8,5,7,6]
     selected=[queries[(i+phase)%12] for i in design]
    else:selected=queries[offset:]+queries[:offset]
    for ordinal,(method,args) in enumerate(selected):
     result,ms=s.call(method,**args);assert result==expected[method],(size,variant,method,'semantic mismatch')
     if steady:row['samples'].append(dict(method=method,ms=ms,round=round,measuredRound=measured,ordinal=ordinal))
    if steady:measured+=1
    round+=1;time.sleep(max(0,.1-(time.monotonic()-began)))
  finally:s.close()
  assert len(row['samples'])==12*rounds
  if order=='balanced':
   for method in names:
    assert all(sum(x['method']==method and x['ordinal']==position for x in row['samples'])==rounds//12 for position in range(12))
  rows.append(row);save('samples.json',rows);print(size,index,variant,'all12 operations passed',flush=True)
 for method,args in queries:
  stats={variant:[trusted.stats([x['ms'] for x in row['samples'] if x['method']==method]) for row in rows if row['size']==int(size) and row['variant']==variant] for variant in ['baseline','candidate']}
  comparisons.append(dict(size=int(size),method=method,stats=stats,medianRatio=statistics.median(x['median'] for x in stats['candidate'])/statistics.median(x['median'] for x in stats['baseline']),p90Ratio=statistics.median(x['p90'] for x in stats['candidate'])/statistics.median(x['p90'] for x in stats['baseline'])))
 # Rename must remain a preview. Retain exact source identities after all sessions.
 for relative,digest in frozen['hashes'].items():assert hashlib.sha256((Path(f['root'])/relative).read_bytes()).hexdigest()==digest
assert len(rows)==len({(row['size'],row['index'],row['variant']) for row in rows})
save('result.json',dict(status='passed',scope='All twelve APIs; descriptive direct-worker screen, not MCP/Glider timing. Rename forces fresh full validation and intentionally affects following operations.',identicalControl=control or None,actualVariants=actual,order=order,rounds=rounds,sessions=sessions,sizes=sizes,measuredChecks=sum(len(r['samples']) for r in rows),comparisons=comparisons))
shutil.copy2(__file__,out/'adapter-source.py')

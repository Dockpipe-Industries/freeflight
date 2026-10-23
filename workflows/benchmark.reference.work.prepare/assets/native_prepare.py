# SPDX-License-Identifier: Apache-2.0
"""Independent native-only scope; never retries or relabels the managed failure."""
import hashlib,json,shutil,statistics,subprocess,sys
from pathlib import Path
repo=Path.cwd();assets=Path(__file__).parent;root=repo/'bin/.local/benchmarks/reference-context';out=root/'native-work-probe-v1';out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):(out/n).write_text(json.dumps(v,indent=2)+'\n')
def command(args,name):
 with (out/name).open('w') as f:subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True,cwd=repo)
failed=root/'work-probe-v1/calibration-result.json';assert json.loads(failed.read_text())['status']=='failed'
for p in assets.iterdir():
 if p.is_file():shutil.copy2(p,out/p.name)
lib=out/'libffworkprobe.dylib';command(['c++','-std=c++23','-O2','-dynamiclib',str(out/'work_helper.cpp'),'-install_name',str(lib),'-o',str(lib)],'helper-build.log')
command(['c++','-std=c++23','-O2',str(out/'NativeCalibration.cpp'),str(lib),'-o',str(out/'native-calibration')],'calibration-build.log')
command([str(out/'native-calibration')],'native-calibration.jsonl')
rows=[json.loads(line) for line in (out/'native-calibration.jsonl').read_text().splitlines()];records=[]
for x in rows:
 if x['kind']=='nested':
  v={k:x['outer'][k]-x['inner'][k] for k in ['instructions','cycles','cpuNs']}
  for k in v:assert v[k]>=0 and v[k]==x['pre'][k]+x['post'][k]
  records.append(dict(**{k:x[k] for k in ['thread','repeat','size','gap','factor']},delta=v))
ratios=[];variability=[]
for thread in ['main','executor']:
 for size in [10000,50000,100000,500000]:
  for gap in [0,1]:
   a={factor:[x['delta']['instructions'] for x in records if x['thread']==thread and x['size']==size and x['gap']==gap and x['factor']==factor] for factor in [1,2]}
   ratios.append(dict(thread=thread,size=size,gap=gap,ratio=statistics.median(a[2])/statistics.median(a[1])))
   for factor,values in a.items():variability.append(dict(thread=thread,size=size,gap=gap,factor=factor,median=statistics.median(values),rangeFraction=(max(values)-min(values))/statistics.median(values)))
empty=sorted(x['delta']['instructions'] for x in rows if x['kind']=='empty');floor=4*empty[int(.99*len(empty))]
valid=all(1.7<x['ratio']<2.3 for x in ratios if x['size']==10000) and all(1.8<x['ratio']<2.2 for x in ratios if x['size']>=50000) and all(x['rangeFraction']<.05 for x in variability if x['size']>=50000)
proof=dict(status='passed' if valid else 'failed',scope='Native-only calling-thread snapshots with reader/caller blocked, small complement around3msnestedwait; managed experiment remains failed/unresolved.',ratios=ratios,variability=variability,emptyInstructionP99=empty[int(.99*len(empty))],resolutionFloor=floor,practicalFraction=.05,rawSha256=sha(out/'native-calibration.jsonl'),failedManagedSha256=sha(failed),decision='Require all scaling checks and<5%repeat range at>=50000iterations before corebuild/time; smaller samples retained ascharacterization. During measurement, no near-count interpretation if calibrationfloor/observedvariability cannotfit5%band. No overhead subtraction.')
save('calibration-result.json',proof);print('Native-only calibration',proof['status'],'resolution',floor,flush=True);assert valid,'Stop native-only experiment after failed qualification'
prepared=repo/'bin/.local/benchmarks/response-copies/json-moves-v2';config=json.loads((prepared/'manifest.json').read_text());profile=prepared/'fixed-payload-profile-v1';cpu=prepared/'pacing-worker-cpu-v1';old=json.loads((profile/'run-manifest.json').read_text())
for name,h in old['sourceHashes']['baseline'].items():assert sha(profile/'baseline-source'/name)==h
source=out/'core-source';shutil.copytree(profile/'baseline-source',source);(source/'include/freeflight/work_probe.hpp').write_bytes((assets/'native_header.hpp').read_bytes())
p=source/'include/freeflight/native_bench.hpp';s=p.read_text();s='#include "freeflight/work_probe.hpp"\n'+s;s=s.replace('wall.clear();cpuStages.clear();workerIds=nlohmann::json::array();','WorkProbe::reset();wall.clear();cpuStages.clear();workerIds=nlohmann::json::array();');s=s.replace('const auto line="CORE_PROFILE "+value.dump()', 'value["work"]=WorkProbe::export_json();\n    const auto line="CORE_PROFILE "+value.dump()');p.write_text(s)
p=source/'src/main.cpp';s=p.read_text();assert s.count('auto serverStart=NativeBench::stamp();')==1;s=s.replace('auto serverStart=NativeBench::stamp();','WorkProbe::Span workServer(0);\n                    auto serverStart=NativeBench::stamp();');s=s.replace('NativeBench::add("serverCall",serverStart);','NativeBench::add("serverCall",serverStart);\n                    workServer.finish();');p.write_text(s)
p=source/'src/process.cpp';s=p.read_text();assert s.count('NativeBench::Scope requestScope("workerRoundTrip");')==1;s=s.replace('NativeBench::Scope requestScope("workerRoundTrip");','NativeBench::Scope requestScope("workerRoundTrip");\n    WorkProbe::Span workRoundTrip(1);');p.write_text(s)
p=source/'CMakeLists.txt';p.write_text(p.read_text()+f'\ntarget_link_libraries(freeflight PRIVATE "{lib}")\nif(TARGET freeflight_process_tests)\n target_link_libraries(freeflight_process_tests PRIVATE "{lib}")\nendif()\n')
cmake=config['cmake'];build=out/'core-build'
for args,name in [([cmake,'-S',str(source),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DFETCHCONTENT_SOURCE_DIR_JSON='+str(repo/'bin/.local/build/_deps/json-src')],'configure'),([cmake,'--build',str(build),'--parallel','2'],'build'),([str(Path(cmake).with_name('ctest')),'--test-dir',str(build),'--output-on-failure'],'native'),([sys.executable,'-B',str(repo/'tests/protocol.py'),str(build/'freeflight')],'protocol')]:command(args,'core-'+name+'.log')
w=json.loads((cpu/'cpu-observer.json').read_text());dll=cpu/'cpu-worker-build/bin/FreeFlight.Roslyn/release/FreeFlight.Roslyn.dll';assert sha(dll)==w['workerSha256']
proofs=[cpu/'cpu-observer.json',cpu/'test_worker.py.log',cpu/'test_trusted.py.log',out/'calibration-result.json',out/'native-calibration.jsonl',root/'work-design-review-v1.json']
for test,h in w['qualificationHashes'].items():assert sha(cpu/(test+'.log'))==h and 'Unhandled exception' not in (cpu/(test+'.log')).read_text()
manifest=dict(status='passed',core=dict(path=str(build/'freeflight'),sha256=sha(build/'freeflight')),workerDll=str(dll),workerSha256=sha(dll),helper=str(lib),helperSha256=sha(lib),calibration=proof,sourceHashes={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()},qualificationHashes={str(p):sha(p) for p in proofs+[out/('core-'+name+'.log') for name in ['configure','build','native','protocol']]},adapterSha256=sha(Path(__file__)),failedManagedSha256=sha(failed),scope='Only generated core own-process raw work counters; existing CPU-stage worker reused unchanged, no managed instruction/alloc/progress observer. Native-only complement is allcoreprocessactivity, not routingthread-only or managedFindReferences inference.')
save('manifest.json',manifest);print('Native-only generated core/protocol gates passed; worker reused, managed work unresolved',flush=True)

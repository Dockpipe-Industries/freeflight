# SPDX-License-Identifier: Apache-2.0
"""Only generated copies; calibration must pass before probe builds and qualification."""
import hashlib,json,shutil,statistics,subprocess,sys
from pathlib import Path
repo=Path.cwd();assets=Path(__file__).parent;root=repo/'bin/.local/benchmarks/reference-context';caps=root/'work-capabilities-v1';assert json.loads((caps/'result.json').read_text())['supported']
out=root/'work-probe-v1';out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,v):(out/name).write_text(json.dumps(v,indent=2)+'\n')
def command(args,log):
 with (out/log).open('w') as f:subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True,cwd=repo)
prepared=repo/'bin/.local/benchmarks/response-copies/json-moves-v2';config=json.loads((prepared/'manifest.json').read_text());dotnet=config['dotnet'];cmake=config['cmake'];cpu=prepared/'pacing-worker-cpu-v1';profile=prepared/'fixed-payload-profile-v1'
metadata=json.loads((cpu/'cpu-observer.json').read_text());assert sha(cpu/'cpu-worker-source/workers/roslyn/Program.cs')==metadata['programSha256']
for name,h in json.loads((profile/'run-manifest.json').read_text())['sourceHashes']['baseline'].items():assert sha(profile/'baseline-source'/name)==h
shutil.copy2(assets/'work_helper.cpp',out/'work_helper.cpp');lib=out/'libffworkprobe.dylib';command(['c++','-std=c++23','-O2','-dynamiclib',str(out/'work_helper.cpp'),'-o',str(lib)],'helper-build.log')
helper=(assets/'managed_helper.cs').read_text().replace('@LIB@',str(lib));cal=out/'calibration';cal.mkdir();(cal/'WorkMeter.cs').write_text(helper);shutil.copy2(assets/'Calibration.cs',cal/'Program.cs')
(cal/'Calibration.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net11.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup></Project>\n')
command([dotnet,'build',str(cal/'Calibration.csproj'),'-c','Release','--disable-build-servers','--artifacts-path',str(out/'calibration-build')],'managed-calibration-build.log')
command([dotnet,str(out/'calibration-build/bin/Calibration/release/Calibration.dll')],'managed-calibration.jsonl')
rows=[json.loads(line) for line in (out/'managed-calibration.jsonl').read_text().splitlines()];work=[x for x in rows if x['kind']=='work']
ratios=[]
for mode in ['direct','async','joined']:
 for size in [25000,100000,1000000]:
  a={f:[x['delta']['instructions'] for x in work if x['mode']==mode and x['size']==size and x['factor']==f] for f in [1,2]}
  ratios.append(dict(mode=mode,size=size,ratio=statistics.median(a[2])/statistics.median(a[1]),oneMedian=statistics.median(a[1]),twoMedian=statistics.median(a[2])))
empty=sorted(x['delta']['instructions'] for x in rows if x['kind']=='empty');floor=4*empty[int(.99*len(empty))]
valid=all(1.7<x['ratio']<2.3 for x in ratios if x['size']==25000) and all(1.8<x['ratio']<2.2 for x in ratios if x['size']!=25000)
for x in rows:
 if x['kind']=='nested':
  for key in ['instructions','cycles','cpuNs']:
   assert x['outer'][key]>=x['inner'][key] and x['outer'][key]-x['inner'][key]==x['pre'][key]+x['post'][key]
proof=dict(status='passed' if valid else 'failed',ratios=ratios,emptyInstructionP99=empty[int(.99*len(empty))],smallestResolvableInstructionDifference=floor,practicalEquivalenceFraction=.05,emptyPairWallMedianNs=statistics.median(x['delta']['wallNs'] for x in rows if x['kind']=='empty'),helperSha256=sha(lib),observationsSha256=sha(out/'managed-calibration.jsonl'),interpretationRule='Observed instruction growth if delta minus resolution floor >5%immediate in bothprobe sessions and block directions positive. Observed near-count evidence only if abs(delta)+floor <=5%immediate in bothsessions/all8blockpairs. Otherwise unresolved. Near-count+higherCPU/instruction supports lower aggregate throughput, not frequency or foreground-work equivalence. No universal overhead subtraction.')
save('calibration-result.json',proof);assert valid,'Do not build/time probe after failed short managed calibration'
# Generated worker preserves the exact FindReferences overload and cancellation token.
workerSource=out/'worker-source';shutil.copytree(cpu/'cpu-worker-source',workerSource);program=workerSource/'workers/roslyn/Program.cs';s=program.read_text()
old='IEnumerable<ReferencedSymbol> references; using(DefinitionCost.Scope("findReferences")) references=await SymbolFinder.FindReferencesAsync(symbolAt,workspace.CurrentSolution,token);';assert s.count(old)==1
s=s.replace(old,'var workBefore=WorkMeter.Read();\n                '+old+'\n                var workAfter=WorkMeter.Read();\n                WorkMeter.Last.Value=new {before=workBefore,after=workAfter};')
s=s.replace('public static void Begin(){Values.Value=new();Counters.Value=new();}','public static void Begin(){Values.Value=new();Counters.Value=new();WorkMeter.Last.Value=null;}')
assert 'previousLogMs=PreviousLogMs}' in s;s=s.replace('previousLogMs=PreviousLogMs}','previousLogMs=PreviousLogMs,work=WorkMeter.Last.Value}')
# IncludeFields is required for the fixed-layout, raw integer stamp fields.
s=s.replace('JsonSerializer.Serialize(new {id,method,stages=Values.Value,counters=Counters.Value,previousLogMs=PreviousLogMs,work=WorkMeter.Last.Value})','JsonSerializer.Serialize(new {id,method,stages=Values.Value,counters=Counters.Value,previousLogMs=PreviousLogMs,work=WorkMeter.Last.Value},new JsonSerializerOptions {IncludeFields=true})')
program.write_text(s+'\n'+helper)
command([dotnet,'build',str(workerSource/'workers/roslyn/FreeFlight.Roslyn.csproj'),'-c','Release','-p:RestoreLockedMode=true','--disable-build-servers','--artifacts-path',str(out/'worker-build')],'worker-build.log')
dll=out/'worker-build/bin/FreeFlight.Roslyn/release/FreeFlight.Roslyn.dll'
for test in ['test_worker.py','test_trusted.py']:
 command([sys.executable,'-B',str(repo/'workers/roslyn'/test),dotnet,str(dll)],test+'.log');assert 'Unhandled exception' not in (out/(test+'.log')).read_text()
# Preserve the baseline native diagnostic and add fixed-storage work brackets only.
coreSource=out/'core-source';shutil.copytree(profile/'baseline-source',coreSource)
header='''#pragma once
#include <cstdint>
#include <nlohmann/json.hpp>
namespace WorkProbe {
struct Stamp {uint64_t instructions,cycles,cpuNs,beginNs,endNs;int32_t pid,status;};
static_assert(sizeof(Stamp)==48);
extern "C" int ffwork_read(Stamp*);
struct Record {Stamp before{},after{};bool valid=false;};
inline thread_local Record records[2];
inline void reset(){records[0]={};records[1]={};}
inline Stamp read(){Stamp s{};const int rc=ffwork_read(&s);if(rc!=0)s.status=rc;return s;}
struct Span {int index;Stamp before;bool done=false;explicit Span(int i):index(i),before(read()){} void finish() noexcept {if(!done){auto after=read();records[index]={before,after,true};done=true;}}~Span(){finish();}};
inline nlohmann::json stamp(Stamp s){return {{"instructions",s.instructions},{"cycles",s.cycles},{"cpuNs",s.cpuNs},{"beginNs",s.beginNs},{"endNs",s.endNs},{"pid",s.pid},{"status",s.status}};}
inline nlohmann::json export_json(){auto j=nlohmann::json::object();for(int i=0;i<2;++i)if(records[i].valid)j[i==0?"serverCall":"workerRoundTrip"]={{"before",stamp(records[i].before)},{"after",stamp(records[i].after)}};return j;}
}
'''
(coreSource/'include/freeflight/work_probe.hpp').write_text(header)
p=coreSource/'include/freeflight/native_bench.hpp';s=p.read_text();s='#include "freeflight/work_probe.hpp"\n'+s;s=s.replace('wall.clear();cpuStages.clear();workerIds=nlohmann::json::array();','WorkProbe::reset();wall.clear();cpuStages.clear();workerIds=nlohmann::json::array();');s=s.replace('const auto line="CORE_PROFILE "+value.dump()', 'value["work"]=WorkProbe::export_json();\n    const auto line="CORE_PROFILE "+value.dump()');p.write_text(s)
p=coreSource/'src/main.cpp';s=p.read_text();assert s.count('auto serverStart=NativeBench::stamp();')==1;s=s.replace('auto serverStart=NativeBench::stamp();','WorkProbe::Span workServer(0);\n                    auto serverStart=NativeBench::stamp();');s=s.replace('NativeBench::add("serverCall",serverStart);','NativeBench::add("serverCall",serverStart);\n                    workServer.finish();');p.write_text(s)
p=coreSource/'src/process.cpp';s=p.read_text();assert s.count('NativeBench::Scope requestScope("workerRoundTrip");')==1;s=s.replace('NativeBench::Scope requestScope("workerRoundTrip");','NativeBench::Scope requestScope("workerRoundTrip");\n    WorkProbe::Span workRoundTrip(1);');p.write_text(s)
p=coreSource/'CMakeLists.txt';p.write_text(p.read_text()+f'\ntarget_link_libraries(freeflight PRIVATE "{lib}")\n')
build=out/'core-build'
for args in [[cmake,'-S',str(coreSource),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DFETCHCONTENT_SOURCE_DIR_JSON='+str(repo/'bin/.local/build/_deps/json-src')],[cmake,'--build',str(build),'--parallel','2'],[str(Path(cmake).with_name('ctest')),'--test-dir',str(build),'--output-on-failure'],[sys.executable,'-B',str(repo/'tests/protocol.py'),str(build/'freeflight')]]:
 name='core-'+('configure' if '-S' in args else 'build' if '--build' in args else 'native' if '--test-dir' in args else 'protocol')+'.log';command(args,name)
manifest=dict(status='passed',core=dict(path=str(build/'freeflight'),sha256=sha(build/'freeflight')),workerDll=str(dll),workerSha256=sha(dll),helper=str(lib),helperSha256=sha(lib),calibration=proof,capabilityReceiptSha256=sha(caps/'result.json'),sources={str(p.relative_to(out)):sha(p) for base in [coreSource,workerSource] for p in base.rglob('*') if p.is_file()},qualificationHashes={name:sha(out/name) for name in ['calibration-result.json','managed-calibration.jsonl','worker-build.log','test_worker.py.log','test_trusted.py.log','core-configure.log','core-build.log','core-native.log','core-protocol.log']},adapterSha256=sha(Path(__file__)),scope='Generated-only process work probe; no allocation scans/progress callbacks/source policy changes. Raw process instruction/cycle/CPU stamps, fixed-storage nested core spans; logging/JSON occurs after endpoints. Not foreground-only or frequency telemetry.')
for p in assets.iterdir():
 if p.is_file():shutil.copy2(p,out/p.name)
save('manifest.json',manifest);print('Generated work probe and short-interval calibration/worker/core/protocol gates passed',flush=True)

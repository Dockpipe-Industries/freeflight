"""Diagnostic only: replay a saved semantic payload, preserve every raw sample."""
import hashlib,json,os,platform,statistics,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[3]
payload=Path(os.environ['FREEFLIGHT_RESPONSE_PAYLOAD']).resolve()
out=root/'bin/.local/benchmarks/response'/os.environ['FREEFLIGHT_RESPONSE_LABEL']
out.mkdir(parents=True,exist_ok=False)
source=Path(__file__).with_name('response_cost.cpp')
header=root/'bin/.local/build/_deps/json-src/single_include'
assert (header/'nlohmann/json.hpp').is_file(),'Run core.build to provision pinned nlohmann 3.12.0 first'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
provenance=dict(platform=platform.platform(),compiler=subprocess.check_output(['c++','--version'],text=True),payload=str(payload),payloadSha256=sha(payload),sourceSha256=sha(source),headerSha256=sha(header/'nlohmann/json.hpp'),limitations=['Instrumented allocations and isolated response construction only; not MCP latency.','Three fresh processes, alternating construction order; parsing and equal input copies excluded.'])
(out/'provenance.json').write_text(json.dumps(provenance,indent=2))
subprocess.run(['c++','-std=c++23','-O3','-I'+str(header),str(source),'-o',str(out/'response-cost')],check=True)
summary=[]
for session in range(3):
 raw=subprocess.check_output([str(out/'response-cost'),str(payload)],text=True)
 (out/f'session-{session}.json').write_text(raw)
 result=json.loads(raw);assert result['byteEqualityCases']==14
 for moved in (False,True):
  rows=[r for r in result['samples'] if r['moved']==moved];times=sorted(r['ms'] for r in rows)
  summary.append(dict(session=session,moved=moved,median=statistics.median(times),p90=times[89],maximum=max(times),allocationCalls=statistics.median(r['allocations'] for r in rows),allocatedBytes=statistics.median(r['allocatedBytes'] for r in rows)))
(out/'summary.json').write_text(json.dumps(dict(status='passed',rows=summary),indent=2))
print(json.dumps(summary,indent=2))

# SPDX-License-Identifier: Apache-2.0
"""Own-process public counter calibration; never changes profiling permissions."""
import hashlib,json,subprocess
from pathlib import Path
repo=Path.cwd();out=repo/'bin/.local/benchmarks/reference-context/work-capabilities-v1';out.mkdir(exist_ok=False)
source=r'''
#include <libproc.h>
#include <sys/resource.h>
#include <unistd.h>
#include <time.h>
#include <chrono>
#include <vector>
#include <algorithm>
#include <iostream>
#include <cstdint>
#include <stdexcept>
struct Snapshot { uint64_t instructions,cycles,cpuNs; };
Snapshot read() {
 rusage_info_v4 info{};timespec cpu{};
 if(proc_pid_rusage(getpid(),RUSAGE_INFO_V4,reinterpret_cast<rusage_info_t*>(&info))!=0)throw std::runtime_error("proc_pid_rusage failed");
 if(clock_gettime(CLOCK_PROCESS_CPUTIME_ID,&cpu)!=0)throw std::runtime_error("CPU clock failed");
 return {info.ri_instructions,info.ri_cycles,uint64_t(cpu.tv_sec)*1000000000+uint64_t(cpu.tv_nsec)};
}
volatile uint64_t sink=3;
void work(uint64_t n) {uint64_t x=sink;for(uint64_t i=0;i<n;++i){x^=x<<13;x^=x>>7;x^=x<<17;}sink=x;}
void emit(const char* name,int rep,uint64_t n) {
 auto a=read();auto start=std::chrono::steady_clock::now();
 if(n)work(n);else usleep(50000);
 auto elapsed=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();auto b=read();
 if(b.instructions<a.instructions||b.cycles<a.cycles||b.cpuNs<a.cpuNs)throw std::runtime_error("Counter went backwards");
 std::cout<<"{\"name\":\""<<name<<"\",\"repeat\":"<<rep<<",\"iterations\":"<<n<<",\"instructions\":"<<b.instructions-a.instructions<<",\"cycles\":"<<b.cycles-a.cycles<<",\"cpuNs\":"<<b.cpuNs-a.cpuNs<<",\"wallMs\":"<<elapsed<<"}\n";
}
int main(){
 std::cout<<"{\"name\":\"abi\",\"flavor\":"<<RUSAGE_INFO_V4<<",\"rusageBytes\":"<<sizeof(rusage_info_v4)<<",\"instructionOffset\":"<<offsetof(rusage_info_v4,ri_instructions)<<",\"cycleOffset\":"<<offsetof(rusage_info_v4,ri_cycles)<<"}\n";
 for(int r=0;r<3;++r){emit("one",r,1000000);emit("two",r,2000000);emit("sleep",r,0);}
 std::vector<double> pairs;
 for(int i=0;i<1000;++i){auto start=std::chrono::steady_clock::now();auto a=read();auto b=read();pairs.push_back(std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count());}
 std::sort(pairs.begin(),pairs.end());std::cout<<"{\"name\":\"overhead\",\"pairMedianMs\":"<<pairs[500]<<",\"pairP90Ms\":"<<pairs[900]<<"}\n";
}
'''
(out/'calibration.cpp').write_text(source)
with (out/'build.log').open('w') as log:subprocess.run(['c++','-std=c++23','-O2',str(out/'calibration.cpp'),'-o',str(out/'calibration')],stdout=log,stderr=subprocess.STDOUT,check=True)
result=subprocess.run([str(out/'calibration')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);(out/'calibration.jsonl').write_text(result.stdout);(out/'calibration.stderr').write_text(result.stderr);result.check_returncode()
rows=[json.loads(line) for line in result.stdout.splitlines()]
ratios=[next(x['instructions'] for x in rows if x['name']=='two' and x['repeat']==r)/max(1,next(x['instructions'] for x in rows if x['name']=='one' and x['repeat']==r)) for r in range(3)]
supported=all(1.8<x<2.2 for x in ratios) and all(x['instructions']>0 and x['cycles']>0 for x in rows if x['name'] in ['one','two'])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=dict(status='passed' if supported else 'unsupported',supported=supported,ratios=ratios,observations=rows,hashes={n:sha(out/n) for n in ['calibration.cpp','calibration','calibration.jsonl','build.log']},adapterSha256=sha(Path(__file__)),scope='Own-process public proc_pid_rusage counters; no privileged profiler, permission/settings changes, affinity or power changes. Functional loop-scaling calibration, not proof of foreground/thread attribution or frequency measurement.')
(out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))

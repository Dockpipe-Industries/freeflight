// SPDX-License-Identifier: Apache-2.0
#include <libproc.h>
#include <sys/resource.h>
#include <unistd.h>
#include <time.h>
#include <cstdint>
#include <cerrno>
struct WorkStamp { uint64_t instructions,cycles,cpuNs,beginNs,endNs; int32_t pid,status; };
static uint64_t nanos(timespec t){return uint64_t(t.tv_sec)*1000000000+uint64_t(t.tv_nsec);}
extern "C" int ffwork_read(WorkStamp* s){
 *s={};s->pid=getpid();timespec begin{},end{},cpu{};rusage_info_v4 info{};
 if(clock_gettime(CLOCK_MONOTONIC,&begin)!=0){s->status=-errno;return s->status;}
 if(proc_pid_rusage(s->pid,RUSAGE_INFO_V4,reinterpret_cast<rusage_info_t*>(&info))!=0){s->status=-errno;return s->status;}
 if(clock_gettime(CLOCK_PROCESS_CPUTIME_ID,&cpu)!=0){s->status=-errno;return s->status;}
 if(clock_gettime(CLOCK_MONOTONIC,&end)!=0){s->status=-errno;return s->status;}
 s->instructions=info.ri_instructions;s->cycles=info.ri_cycles;s->cpuNs=nanos(cpu);s->beginNs=nanos(begin);s->endNs=nanos(end);return 0;
}
extern "C" uint64_t ffwork_loop(uint64_t n,uint64_t x){for(uint64_t i=0;i<n;++i){x^=x<<13;x^=x>>7;x^=x<<17;}return x;}
extern "C" int ffwork_stamp_bytes(){return sizeof(WorkStamp);}

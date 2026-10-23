// SPDX-License-Identifier: Apache-2.0
#include <libproc.h>
#include <sys/resource.h>
#include <mach/mach_time.h>
#include <time.h>
#include <cstdint>
#include <cerrno>
#include <cstddef>
struct Stamp {uint64_t instructions,cycles,userMach,systemMach,start,begin,end;uint32_t numer,denom;int32_t pid,status;};
static uint64_t ns(clockid_t clock){timespec t{};if(clock_gettime(clock,&t))return 0;return uint64_t(t.tv_sec)*1000000000+t.tv_nsec;}
extern "C" uint64_t ff_now(){return ns(CLOCK_MONOTONIC);}
extern "C" uint64_t ff_cpu(){return ns(CLOCK_PROCESS_CPUTIME_ID);}
extern "C" int ff_read(int pid,Stamp* s){*s={};s->pid=pid;s->begin=ff_now();rusage_info_v4 info{};mach_timebase_info_data_t tb{};int e=mach_timebase_info(&tb);s->numer=tb.numer;s->denom=tb.denom;if(e){s->status=-e;return s->status;}if(proc_pid_rusage(pid,RUSAGE_INFO_V4,reinterpret_cast<rusage_info_t*>(&info))){s->status=-errno;return s->status;}s->instructions=info.ri_instructions;s->cycles=info.ri_cycles;s->userMach=info.ri_user_time;s->systemMach=info.ri_system_time;s->start=info.ri_proc_start_abstime;s->end=ff_now();return 0;}
extern "C" int ff_size(){return sizeof(Stamp);}
extern "C" uint64_t ff_loop(uint64_t n,uint64_t x){for(uint64_t i=0;i<n;++i){x^=x<<13;x^=x>>7;x^=x<<17;}return x;}

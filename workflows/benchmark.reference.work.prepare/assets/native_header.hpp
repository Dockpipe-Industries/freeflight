#pragma once
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

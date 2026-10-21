# SPDX-License-Identifier: Apache-2.0
"""Generated-source native MCP diagnostics. Never modify production sources."""
from pathlib import Path
import json
import gc
import time

def assert_clean_worker_log(path):
    # The pinned trusted test checks semantic assertions but historically did not
    # assert the worker's EOF exit status. Do not let its successful Python exit
    # hide a worker crash, including a diagnostic-only shutdown failure.
    text = Path(path).read_text()
    assert 'Unhandled exception.' not in text, 'Worker crashed during qualification: '+str(path)

HEADER = r'''
#pragma once
#include <nlohmann/json.hpp>
#include <chrono>
#include <map>
#include <string>
#include <sys/resource.h>
#include <time.h>
#include <unistd.h>
namespace NativeBench {
using Clock = std::chrono::steady_clock;
struct Stamp { Clock::time_point wall; double cpu; };
inline double cpu() { timespec t{}; clock_gettime(CLOCK_THREAD_CPUTIME_ID, &t); return t.tv_sec*1000.0+t.tv_nsec/1e6; }
inline Stamp stamp() { return {Clock::now(),cpu()}; }
inline thread_local bool active=false;
inline thread_local std::map<std::string,double> wall,cpuStages;
inline thread_local nlohmann::json workerIds;
inline thread_local Stamp began;
inline thread_local rusage before{};
inline void add(const std::string& name, Stamp s) {
    if (!active) return;
    wall[name]+=std::chrono::duration<double,std::milli>(Clock::now()-s.wall).count();
    cpuStages[name]+=cpu()-s.cpu;
}
struct Scope { std::string name; Stamp start; Scope(std::string n):name(std::move(n)),start(stamp()){} ~Scope(){add(name,start);} };
inline void begin(Clock::time_point queued) {
    wall.clear();cpuStages.clear();workerIds=nlohmann::json::array();
    began=stamp();getrusage(RUSAGE_SELF,&before);active=true;
    wall["queueWait"]=std::chrono::duration<double,std::milli>(began.wall-queued).count();
}
inline std::string dump(const nlohmann::json& value,const std::string& name) { Scope scope(name);return value.dump(); }
inline void worker(const nlohmann::json& id) { if(active)workerIds.push_back(id); }
inline void end(const nlohmann::json& id,const std::string& method) {
    add("coreTotal",began);rusage after{};getrusage(RUSAGE_SELF,&after);active=false;
    auto ms=[](timeval t){return t.tv_sec*1000.0+t.tv_usec/1000.0;};
    nlohmann::json value={{"id",id},{"method",method},{"workerIds",workerIds},{"stages",wall},{"threadCpuStages",cpuStages},
        {"processCpuMs",ms(after.ru_utime)+ms(after.ru_stime)-ms(before.ru_utime)-ms(before.ru_stime)},
        {"voluntarySwitches",after.ru_nvcsw-before.ru_nvcsw},{"involuntarySwitches",after.ru_nivcsw-before.ru_nivcsw}};
    const auto line="CORE_PROFILE "+value.dump()+"\n";
    (void)::write(STDERR_FILENO,line.data(),line.size());
}
}
'''

def instrument_core(root):
    root=Path(root)
    (root/'include/freeflight/native_bench.hpp').write_text(HEADER)
    p=root/'src/main.cpp';s=p.read_text()
    def replace(old,new):
        nonlocal s
        assert s.count(old)==1, 'Core profile anchor drift: '+old[:80]
        s=s.replace(old,new)
    s='#include "freeflight/native_bench.hpp"\n'+s
    replace('    Json clientRoots = nullptr;', '    Json clientRoots = nullptr;\n    NativeBench::Clock::time_point queued = NativeBench::Clock::now();')
    replace('            std::cout << response.dump() << \'\\n\' << std::flush;', '''            auto serialized=NativeBench::dump(response,"mcpSerialize");
            NativeBench::Scope writeScope("mcpWrite");
            std::cout << serialized << '\\n' << std::flush;''')
    replace('        auto result = [&](const Json &id, Json value, bool modern) {', '        auto result = [&](const Json &id, Json value, bool modern) {\n            NativeBench::Scope resultScope("resultEnvelope");')
    replace('                Json response;\n                try {', '                NativeBench::begin(job->queued);\n                Json response;\n                try {')
    replace('                    auto value = server.call(', '                    auto serverStart=NativeBench::stamp();\n                    auto value = server.call(')
    replace('                                             job->stop.get_token());', '                                             job->stop.get_token());\n                    NativeBench::add("serverCall",serverStart);\n                    auto constructionStart=NativeBench::stamp();')
    replace('value.dump()', 'NativeBench::dump(value,"valueSerialize")')
    replace('                } catch (const freeflight::EngineError &exception) {', '                    NativeBench::add("responseConstruction",constructionStart);\n                } catch (const freeflight::EngineError &exception) {')
    replace('                // Cancellation and delivery share a lock, preventing a post-cancel reply.', '                auto deliveryStart=NativeBench::stamp();\n                // Cancellation and delivery share a lock, preventing a post-cancel reply.')
    replace('                pending.erase(job->id.dump());\n            }\n        });', '                pending.erase(job->id.dump());\n                NativeBench::add("delivery",deliveryStart);\n                NativeBench::end(job->id,job->params.value("name",std::string()));\n            }\n        });')
    p.write_text(s)
    p=root/'src/process.cpp';s=p.read_text();s='#include "freeflight/native_bench.hpp"\n'+s
    replace('nlohmann::json Process::request(const nlohmann::json &message, std::stop_token token) {', 'nlohmann::json Process::request(const nlohmann::json &message, std::stop_token token) {\n    NativeBench::Scope requestScope("workerRoundTrip");\n')
    replace('        throw std::runtime_error("worker request requires an id");', '        throw std::runtime_error("worker request requires an id");\n    NativeBench::worker(message.at("id"));')
    replace('line = message.dump();','line = NativeBench::dump(message,"workerRequestSerialize");')
    replace('        PipeSignalGuard guard;', '        auto pipeWriteStart=NativeBench::stamp();\n        PipeSignalGuard guard;')
    replace("        }\n#endif\n        for (;;) {", "        }\n        NativeBench::add(\"workerPipeWrite\",pipeWriteStart);\n#endif\n        auto receiveStart=NativeBench::stamp();\n        for (;;) {")
    replace('                // Abort before constructing a deeply recursive worker response.', '                NativeBench::add("workerReceive",receiveStart);\n                NativeBench::Scope parseScope("workerResponseParse");\n                // Abort before constructing a deeply recursive worker response.')
    p.write_text(s)

def instrument_worker(root):
    from profile import instrument
    p=Path(root)/'workers/roslyn/Program.cs';instrument(p);s=p.read_text()
    def replace(old,new):
        nonlocal s
        assert s.count(old)==1, 'Native worker profile anchor drift: '+old[:80]
        s=s.replace(old,new)
    replace('                jobs.Add(Task.Run(async () =>', '                var benchQueued=Stopwatch.GetTimestamp();\n                jobs.Add(Task.Run(async () =>')
    replace('                        await gate.WaitAsync(cts.Token);', '                        var benchRunning=Stopwatch.GetTimestamp();\n                        await gate.WaitAsync(cts.Token);\n                        var benchAdmitted=Stopwatch.GetTimestamp();')
    replace('                            BenchProfile.Begin();', '''                            BenchProfile.Begin();
                            BenchProfile.Value("workerQueue",Stopwatch.GetElapsedTime(benchQueued,benchRunning).TotalMilliseconds);
                            BenchProfile.Value("workerGate",Stopwatch.GetElapsedTime(benchRunning,benchAdmitted).TotalMilliseconds);''')
    replace('            lock (outputGate) output.WriteLine(JsonSerializer.Serialize(value, Json));', '''            lock (outputGate) {
                var serializeStart=Stopwatch.GetTimestamp();
                var serialized=JsonSerializer.Serialize(value,Json);
                BenchProfile.Add("workerSerialize",serializeStart);
                var writeStart=Stopwatch.GetTimestamp();
                output.WriteLine(serialized);
                BenchProfile.Add("workerWrite",writeStart);
            }''')
    replace('    public static IDisposable Scope(string stage)', '    public static void Value(string stage,double value) { Stages.Value![stage]=value; }\n    public static IDisposable Scope(string stage)')
    s=s.replace('                            BenchProfile.Begin();','                            var benchPrelude=Stopwatch.GetTimestamp();\n                            BenchProfile.Begin();\n                            BenchProfile.Value("profilePrelude",Stopwatch.GetElapsedTime(benchPrelude).TotalMilliseconds);')
    s=s.replace('                            BenchProfile.End(id, method, invokeMs, Stopwatch.GetElapsedTime(reply).TotalMilliseconds);','                            var benchPostlude=Stopwatch.GetTimestamp();\n                            BenchProfile.End(id, method, invokeMs, Stopwatch.GetElapsedTime(reply).TotalMilliseconds);\n                            BenchProfile.PreviousPostludeMs=Stopwatch.GetElapsedTime(benchPostlude).TotalMilliseconds;')
    s=s.replace('    public static long Reads, Expired, Dirty, Invalidated, Bytes, Reused, Attrs;', '    public static long Reads, Expired, Dirty, Invalidated, Bytes, Reused, Attrs;\n    public static double PreviousPostludeMs;')
    s=s.replace('id, method, invokeMs, replyMs, stages,','id, method, invokeMs, replyMs, stages, previousProfilePostludeMs=PreviousPostludeMs,')
    p.write_text(s)

def install_client(client):
    """Same protocol semantics; timestamps/JSON parse observation in diagnostic runs only."""
    gc_state={'start':0,'pauseNs':0,'collections':0}
    def observed_gc(phase,info):
        if phase=='start':gc_state['start']=time.perf_counter_ns()
        elif phase=='stop':
            gc_state['pauseNs']+=time.perf_counter_ns()-gc_state['start'];gc_state['collections']+=1
    gc.callbacks.append(observed_gc)
    class ProfileSession(client.Session):
        def read_responses(self):
            for line in self.process.stdout:self.responses.put((line,time.perf_counter_ns()))
            self.responses.put((None,time.perf_counter_ns()))
        def request(self,method,params):
            self.sequence+=1;start=time.perf_counter_ns();gcBefore=gc_state['pauseNs'];gcCount=gc_state['collections']
            outgoing=json.dumps({'jsonrpc':'2.0','id':self.sequence,'method':method,'params':{**params,'_meta':self.meta}})+'\n'
            encoded=time.perf_counter_ns();self.process.stdin.write(outgoing);self.process.stdin.flush();written=time.perf_counter_ns()
            deadline=time.monotonic()+120
            while True:
                line,received=self.responses.get(timeout=max(.01,deadline-time.monotonic()));dequeued=time.perf_counter_ns()
                assert line is not None,'MCP server closed before response'
                parseStart=time.perf_counter_ns();response=json.loads(line);parsed=time.perf_counter_ns()
                if 'id' in response:break
                assert response.get('method'),response
            assert response.get('id')==self.sequence and 'error' not in response,response
            assert not response['result'].get('isError'),response
            self.last_request_profile=dict(id=self.sequence,serializeMs=(encoded-start)/1e6,writeMs=(written-encoded)/1e6,
                waitUntilReadMs=(received-written)/1e6,readerQueueMs=(dequeued-received)/1e6,parseMs=(parsed-parseStart)/1e6,responseBytes=len(line.encode()),gcPauseMs=(gc_state['pauseNs']-gcBefore)/1e6,gcCollections=gc_state['collections']-gcCount)
            return response['result']
    client.Session=ProfileSession

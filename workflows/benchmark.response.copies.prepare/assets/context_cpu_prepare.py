# SPDX-License-Identifier: Apache-2.0
"""Generated-only worker process-CPU observer with local ABI/calibration proofs."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path

def prepare(repo,out,parent,config):
 def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
 def command(args,name):
  with (out/name).open('w') as log:subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True)
 native=out/'clock-abi.cpp';native.write_text('#include <time.h>\n#include <iostream>\nint main(){std::cout << "{\\"clockId\\":" << int(CLOCK_PROCESS_CPUTIME_ID) << ",\\"timespecBytes\\":" << sizeof(timespec) << ",\\"secondsBytes\\":" << sizeof(timespec{}.tv_sec) << ",\\"nanosBytes\\":" << sizeof(timespec{}.tv_nsec) << "}\\n";}\n')
 command(['c++','-std=c++23','-O2',str(native),'-o',str(out/'clock-abi')],'clock-abi-build.log')
 abi=json.loads(subprocess.check_output([str(out/'clock-abi')],text=True));assert abi==dict(clockId=12,timespecBytes=16,secondsBytes=8,nanosBytes=8)
 (out/'clock-abi.json').write_text(json.dumps(abi,indent=2)+'\n')
 helper='''internal static class InvocationCpu
{
 [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
 private struct Timespec { public long Seconds; public long Nanoseconds; }
 [System.Runtime.InteropServices.DllImport("libc",SetLastError=true)]
 private static extern int clock_gettime(int id,out Timespec value);
 public static double Read()
 {
  if(!System.OperatingSystem.IsMacOS() || System.Runtime.InteropServices.Marshal.SizeOf<Timespec>()!=16) throw new System.PlatformNotSupportedException("Diagnostic CPU clock ABI");
  if(clock_gettime(12,out var value)!=0)throw new System.IO.IOException("Diagnostic process CPU clock failed");
  return value.Seconds*1000.0+value.Nanoseconds/1e6;
 }
}
'''
 calibration=out/'clock-calibration';calibration.mkdir()
 (calibration/'Clock.cs').write_text(helper)
 (calibration/'Calibration.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net11.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup></Project>\n')
 (calibration/'Program.cs').write_text('''using System.Diagnostics;
using System.Text.Json;
for(int i=0;i<10000;i++)InvocationCpu.Read();
var pairs=new double[2000];
for(int i=0;i<pairs.Length;i++){var start=Stopwatch.GetTimestamp();var a=InvocationCpu.Read();var b=InvocationCpu.Read();if(b<a)throw new Exception("Nonmonotonic CPU clock");pairs[i]=Stopwatch.GetElapsedTime(start).TotalMilliseconds;}
var before=InvocationCpu.Read();var wall=Stopwatch.StartNew();Thread.Sleep(50);var sleepCpu=InvocationCpu.Read()-before;var sleepWall=wall.Elapsed.TotalMilliseconds;
before=InvocationCpu.Read();wall.Restart();long sink=0;while(wall.ElapsedMilliseconds<50)Interlocked.Increment(ref sink);var busyCpu=InvocationCpu.Read()-before;var busyWall=wall.Elapsed.TotalMilliseconds;
if(sleepCpu>=sleepWall*.5 || busyCpu<=busyWall*.1)throw new Exception("CPU/wall distinction failed");
Array.Sort(pairs);Console.WriteLine(JsonSerializer.Serialize(new {status="passed",clock="Darwin CLOCK_PROCESS_CPUTIME_ID",pairMedianMs=pairs[pairs.Length/2],pairP90Ms=pairs[(int)(pairs.Length*.9)],sleepCpuMs=sleepCpu,sleepWallMs=sleepWall,busyCpuMs=busyCpu,busyWallMs=busyWall,sink}));
''')
 command([config['dotnet'],'build',str(calibration/'Calibration.csproj'),'-c','Release','--disable-build-servers','--artifacts-path',str(out/'calibration-build')],'clock-calibration-build.log')
 proof=json.loads(subprocess.check_output([config['dotnet'],str(out/'calibration-build/bin/Calibration/release/Calibration.dll')],text=True));assert proof['status']=='passed'
 (out/'clock-calibration.json').write_text(json.dumps(proof,indent=2)+'\n')
 source=out/'cpu-worker-source';shutil.copytree(parent/'source',source)
 program=source/'workers/roslyn/Program.cs';s=program.read_text();beforeHash=sha(program)
 old='                            var result=await engine.Invoke(method,args,cts.Token);';assert s.count(old)==1
 s=s.replace(old,'                            var invocationCpu=InvocationCpu.Read();\n'+old+'\n                            DefinitionCost.Values.Value!["processCpuInvoke"]=InvocationCpu.Read()-invocationCpu;')
 program.write_text(s+'\n'+helper)
 command([config['dotnet'],'build',str(source/'workers/roslyn/FreeFlight.Roslyn.csproj'),'-c','Release','-p:RestoreLockedMode=true','--disable-build-servers','--artifacts-path',str(out/'cpu-worker-build')],'cpu-worker-build.log')
 dll=out/'cpu-worker-build/bin/FreeFlight.Roslyn/release/FreeFlight.Roslyn.dll'
 for test in ['test_worker.py','test_trusted.py']:
  command([sys.executable,'-B',str(repo/'workers/roslyn'/test),config['dotnet'],str(dll)],test+'.log')
  assert 'Unhandled exception' not in (out/(test+'.log')).read_text()
 metadata=dict(status='passed',scope='Generated-only worker process CPU over invocation, across async continuations/all worker threads. Includes GC/background-thread CPU in that interval; not thread CPU, retired instructions or foreground-only CPU. Two native reads per invocation; calibration is not a complete observer bound.',abi=abi,calibration=proof,parentProgramSha256=beforeHash,programSha256=sha(program),workerSha256=sha(dll),helperSha256=hashlib.sha256(helper.encode()).hexdigest(),nativeClockSourceSha256=sha(native),qualificationHashes={test:sha(out/(test+'.log')) for test in ['test_worker.py','test_trusted.py']})
 (out/'cpu-observer.json').write_text(json.dumps(metadata,indent=2)+'\n')
 return dll,metadata

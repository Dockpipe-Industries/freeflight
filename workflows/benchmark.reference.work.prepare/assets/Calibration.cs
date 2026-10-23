// SPDX-License-Identifier: Apache-2.0
using System.Diagnostics;
using System.Text.Json;
static object Difference(WorkMeter.Stamp a,WorkMeter.Stamp b){if(a.pid!=b.pid||a.status!=0||b.status!=0||b.instructions<a.instructions||b.cycles<a.cycles||b.cpuNs<a.cpuNs||b.beginNs<a.endNs)throw new Exception("Invalid work stamps");return new {instructions=b.instructions-a.instructions,cycles=b.cycles-a.cycles,cpuNs=b.cpuNs-a.cpuNs,wallNs=b.beginNs-a.endNs};}
long sink=0;
for(int i=0;i<1000;i++){var a=WorkMeter.Read();var b=WorkMeter.Read();}
for(int r=0;r<5;r++)foreach(var n in new ulong[]{25000,100000,1000000})foreach(var factor in new ulong[]{1,2})foreach(var mode in new[]{"direct","async","joined"}){
 var before=WorkMeter.Read();
 if(mode=="direct")Interlocked.Exchange(ref sink,(long)WorkMeter.Loop(n*factor,3));
 else if(mode=="async")Interlocked.Exchange(ref sink,(long)await Task.Run(()=>WorkMeter.Loop(n*factor,3)));
 else {var x=Task.Run(()=>WorkMeter.Loop(n*factor/2,3));var y=Task.Run(()=>WorkMeter.Loop(n*factor/2,7));await Task.WhenAll(x,y);Interlocked.Exchange(ref sink,(long)(x.Result^y.Result));}
 var after=WorkMeter.Read();Console.WriteLine(JsonSerializer.Serialize(new {kind="work",repeat=r,size=n,factor,mode,delta=Difference(before,after)}));
}
for(int r=0;r<500;r++){var a=WorkMeter.Read();var b=WorkMeter.Read();Console.WriteLine(JsonSerializer.Serialize(new {kind="empty",delta=Difference(a,b)}));}
for(int r=0;r<20;r++){
 var a=WorkMeter.Read();Interlocked.Exchange(ref sink,(long)WorkMeter.Loop(100000,3));var b=WorkMeter.Read();Interlocked.Exchange(ref sink,(long)await Task.Run(()=>WorkMeter.Loop(1000000,5)));var c=WorkMeter.Read();Interlocked.Exchange(ref sink,(long)WorkMeter.Loop(100000,7));var d=WorkMeter.Read();
 Console.WriteLine(JsonSerializer.Serialize(new {kind="nested",outer=Difference(a,d),inner=Difference(b,c),pre=Difference(a,b),post=Difference(c,d)}));
}
Console.WriteLine(JsonSerializer.Serialize(new {kind="abi",stampBytes=System.Runtime.InteropServices.Marshal.SizeOf<WorkMeter.Stamp>(),sink}));

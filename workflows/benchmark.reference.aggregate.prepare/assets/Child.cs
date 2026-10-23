// SPDX-License-Identifier: Apache-2.0
using System.Runtime.InteropServices;
using System.Text.Json;
class Native {
 [DllImport("LIBRARY")]internal static extern ulong ff_loop(ulong n,ulong x);
 [DllImport("LIBRARY")]internal static extern ulong ff_now();
 [DllImport("LIBRARY")]internal static extern ulong ff_cpu();
}
class Program {
 static async Task<ulong> Work(ulong n){var a=Task.Run(()=>Native.ff_loop(n/2,3));var b=Task.Run(()=>Native.ff_loop(n/2,7));await Task.WhenAll(a,b);return a.Result^b.Result;}
 static void Wait(ulong t){while(Native.ff_now()<t){var remain=t-Native.ff_now();if(remain<1000000){Thread.Sleep(1);continue;}Thread.Sleep((int)Math.Min(50,remain/1000000));}}
 static async Task Main(){ulong sink=0;for(int i=0;i<1000;i++)sink^=await Work(10000);for(int i=0;i<20;i++)Console.WriteLine(JsonSerializer.Serialize(new {kind="warm",sink}));Console.WriteLine("READY");
 string? line;while((line=Console.ReadLine())!=null){if(line=="CPU"){Console.WriteLine(Native.ff_cpu());continue;}using var d=JsonDocument.Parse(line);ulong start=d.RootElement.GetProperty("start").GetUInt64(),n=d.RootElement.GetProperty("n").GetUInt64();var before=Native.ff_cpu();Console.WriteLine("ARMED");var cycles=new List<object>();for(int i=0;i<16;i++){ulong target=start+(ulong)i*250000000;Wait(target);var begin=Native.ff_now();var result=await Work(n);var end=Native.ff_now();cycles.Add(new {i,target,begin,end,result});}var after=Native.ff_cpu();Console.WriteLine(JsonSerializer.Serialize(new {kind="done",n,before,after,cycles}));}
 }
}

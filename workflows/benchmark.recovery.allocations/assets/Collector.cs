// SPDX-License-Identifier: Apache-2.0
using System.Diagnostics.Tracing;
using System.Text.Json;
using Microsoft.Diagnostics.NETCore.Client;
using Microsoft.Diagnostics.Tracing;
using Microsoft.Diagnostics.Tracing.Etlx;
using Microsoft.Diagnostics.Tracing.Parsers.Clr;
if(args[0]=="collect")
{
    var client=new DiagnosticsClient(int.Parse(args[1]));
    using var session=client.StartEventPipeSession(new[]{
        new EventPipeProvider("Microsoft-Windows-DotNETRuntime",EventLevel.Verbose,0x40000001),
        new EventPipeProvider("FreeFlight-Allocation-Probe",EventLevel.Informational)},requestRundown:true,circularBufferMB:64);
    using var file=File.Create(args[2]);
    var copying=session.EventStream.CopyToAsync(file);
    Console.WriteLine("READY"); Console.ReadLine(); session.Stop(); await copying;
}
else
{
    var etlx=TraceLog.CreateFromEventPipeDataFile(args[1]);
    using var log=new TraceLog(etlx);
    var events=new List<object>();
    foreach(var e in log.Events)
    {
        if(e.ProviderName=="FreeFlight-Allocation-Probe")
            events.Add(new {kind="marker",ms=e.TimeStampRelativeMSec,name=e.EventName,payload=e.PayloadNames.ToDictionary(n=>n,n=>e.PayloadByName(n))});
        if(e is GCAllocationTickTraceData tick)
        {
            var frames=new List<string>();
            for(var frame=e.CallStack();frame!=null && frames.Count<100;frame=frame.Caller)
                frames.Add(frame.CodeAddress.FullMethodName);
            events.Add(new {kind="allocation",ms=e.TimeStampRelativeMSec,type=tick.TypeName,bytes=tick.AllocationAmount64,frames});
        }
    }
    File.WriteAllText(args[2],JsonSerializer.Serialize(new {eventsLost=log.EventsLost,events}));
}

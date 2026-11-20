# SPDX-License-Identifier: Apache-2.0
"""Generated proof harness around the actual Darwin helper; no production test hooks."""
import json, os, pathlib, shutil, subprocess, sys
if len(sys.argv)==1:
    label=os.environ['FREEFLIGHT_METADATA_LABEL'];assert label and all(c.isalnum() or c in '-_' for c in label)
    sdk=shutil.which('dotnet');assert sdk
    source=str(pathlib.Path.cwd());output=str(pathlib.Path.cwd()/'bin/.local'/('metadata-proof-'+label))
else:sdk,source,output=sys.argv[1:4]
source=pathlib.Path(source);out=pathlib.Path(output);out.mkdir(parents=True,exist_ok=False)
text=(source/'workers/roslyn/DarwinMetadataBatch.cs').read_text()
anchor='            if (count < 0) return false;'
assert text.count(anchor)==1
text=text.replace(anchor,'            MetadataTestHooks.AfterBulk?.Invoke(buffer);\n'+anchor)
anchor='        var current = new byte[44];'
assert text.count(anchor)==1
text=text.replace(anchor,'        MetadataTestHooks.BeforeIdentity?.Invoke();\n'+anchor)
opening = '    private (SafeFileHandle? Handle, bool Owned) OpenDirectory(string path, CancellationToken token)\n    {' if 'bool Owned) OpenDirectory' in text else '    private static SafeFileHandle? OpenDirectory(string path, CancellationToken token)\n    {'
text=text.replace(opening, opening+'\n        using var timing = MetadataTestHooks.Scope("openDirectory");')
text=text.replace('            var count = Bulk(handle, ref attributes, buffer, (nuint)capacity, 8);', '            var nativeStart = System.Diagnostics.Stopwatch.GetTimestamp();\n            var count = Bulk(handle, ref attributes, buffer, (nuint)capacity, 8);\n            MetadataTestHooks.Observe("bulkSyscall", System.Diagnostics.Stopwatch.GetElapsedTime(nativeStart).TotalMilliseconds);')
(out/'DarwinMetadataBatch.cs').write_text(text)
(out/'global.json').write_bytes((source/'global.json').read_bytes())
(out/'Proof.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net11.0</TargetFramework><OutputType>Exe</OutputType><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup></Project>')
(out/'Hooks.cs').write_text('''namespace FreeFlight.Roslyn;
internal static class MetadataTestHooks {
 internal static System.Action<byte[]>? AfterBulk; internal static System.Action? BeforeIdentity;
 internal static readonly System.Collections.Generic.Dictionary<string,double> Timings=new();
 internal static void Observe(string name,double ms)=>Timings[name]=Timings.GetValueOrDefault(name)+ms;
 internal static System.IDisposable Scope(string name)=>new Timing(name);
 private sealed class Timing(string name):System.IDisposable { readonly long start=System.Diagnostics.Stopwatch.GetTimestamp(); public void Dispose()=>Observe(name,System.Diagnostics.Stopwatch.GetElapsedTime(start).TotalMilliseconds); }
}''')
(out/'Program.cs').write_text(r'''
using FreeFlight.Roslyn;
using System.Buffers.Binary;
if (!OperatingSystem.IsMacOS()) throw new PlatformNotSupportedException("Darwin metadata proof requires macOS");
var root=Path.Combine(AppContext.BaseDirectory,"fixture");Directory.CreateDirectory(root);
var parent=Path.Combine(root,"members");Directory.CreateDirectory(parent);
var validationRoot=root;
void ValidatePath(string path){var current=validationRoot;foreach(var part in Path.GetRelativePath(validationRoot,path).Split(Path.DirectorySeparatorChar)){current=Path.Combine(current,part);if((File.GetAttributes(current)&FileAttributes.ReparsePoint)!=0)throw new UnauthorizedAccessException("Symlink/reparse paths are not supported");}}
var files=Enumerable.Range(0,64).Select(i=>Path.Combine(parent,$"Member-{i:D3}-é.cs")).ToArray();
foreach(var file in files)File.WriteAllText(file,"class C {}\n");
var groups=new Dictionary<string,Dictionary<string,string>>(StringComparer.Ordinal){[parent]=files.ToDictionary(p=>Path.GetFileName(p)!,p=>p,StringComparer.Ordinal)};
void Require(bool value,string reason){if(!value)throw new Exception(reason);}
void Equal(string file,DarwinMetadataBatch.Metadata data){var info=new FileInfo(file);Require(data.Length==info.Length && data.Modified==info.LastWriteTimeUtc.Ticks,"metadata differs from fresh FileInfo: "+file);}
using(var b=new DarwinMetadataBatch(groups,500000,ValidatePath)){
 foreach(var file in files){Require(b.TryGet(file,parent,default,out var data),"native miss");Equal(file,data);}
 Require(b.Hits==64 && b.Calls>0 && b.Entries==64,"native path not exercised");
}
File.WriteAllText(files[0],"changed contents of different length");File.SetLastWriteTimeUtc(files[0],new DateTime(1960,1,1,0,0,0,DateTimeKind.Utc));
using(var b=new DarwinMetadataBatch(groups,500000,ValidatePath)){Require(b.TryGet(files[0],parent,default,out var data),"changed native miss");Equal(files[0],data);}
var outside=Path.Combine(root,"outside.cs");File.WriteAllText(outside,"outside");
File.Delete(files[1]);File.CreateSymbolicLink(files[1],outside);File.Delete(files[2]);
using(var b=new DarwinMetadataBatch(groups,500000,ValidatePath)){
 Require(!b.TryGet(files[1],parent,default,out _),"symlink accepted");Require(!b.TryGet(files[2],parent,default,out _),"missing accepted");
 Require(b.TryGet(files[3],parent,default,out var data),"regular sibling rejected");Equal(files[3],data);
}
File.Delete(files[1]);File.WriteAllText(files[1],"restored");File.WriteAllText(files[2],"restored");
var moved=parent+"-old";
foreach(var symlink in new[]{false,true}){
 MetadataTestHooks.BeforeIdentity=()=>{Directory.Move(parent,moved);if(symlink)Directory.CreateSymbolicLink(parent,moved);else Directory.CreateDirectory(parent);};
 try{using var b=new DarwinMetadataBatch(groups,500000,ValidatePath);bool rejected=false;try{rejected=!b.TryGet(files[0],parent,default,out _);}catch(UnauthorizedAccessException){rejected=true;}Require(rejected,"replaced directory admitted");}
 finally{MetadataTestHooks.BeforeIdentity=null;Directory.Delete(parent);Directory.Move(moved,parent);}
}
var ancestor=Path.Combine(root,"ancestor");var child=Path.Combine(ancestor,"child");Directory.CreateDirectory(child);
var raceFiles=Enumerable.Range(0,32).Select(i=>Path.Combine(child,$"C{i}.cs")).ToArray();foreach(var file in raceFiles)File.WriteAllText(file,"class C {}");
var raceGroups=new Dictionary<string,Dictionary<string,string>>{[child]=raceFiles.ToDictionary(p=>Path.GetFileName(p)!,p=>p)};
MetadataTestHooks.BeforeIdentity=()=>{Directory.Move(ancestor,ancestor+"-old");Directory.CreateSymbolicLink(ancestor,ancestor+"-old");};
try{using var b=new DarwinMetadataBatch(raceGroups,500000,ValidatePath);bool rejected=false;try{b.TryGet(raceFiles[0],child,default,out _);}catch(UnauthorizedAccessException){rejected=true;}Require(rejected,"same-identity ancestor symlink admitted");}
finally{MetadataTestHooks.BeforeIdentity=null;Directory.Delete(ancestor);Directory.Move(ancestor+"-old",ancestor);}
using(var cts=new CancellationTokenSource()){
 MetadataTestHooks.AfterBulk=_=>cts.Cancel();
 try{using var b=new DarwinMetadataBatch(groups,500000,ValidatePath);bool cancelled=false;try{b.TryGet(files[0],parent,cts.Token,out _);}catch(OperationCanceledException){cancelled=true;}Require(cancelled,"cancellation ignored");}
 finally{MetadataTestHooks.AfterBulk=null;}
}
// Corrupt each relevant record field independently. No malformed metadata is reused.
foreach(var mutate in new Action<byte[]>[]{
 b=>BinaryPrimitives.WriteUInt32LittleEndian(b.AsSpan(0,4),uint.MaxValue),
 b=>BinaryPrimitives.WriteInt32LittleEndian(b.AsSpan(28,4),int.MaxValue),
 b=>BinaryPrimitives.WriteUInt32LittleEndian(b.AsSpan(32,4),uint.MaxValue),
 b=>BinaryPrimitives.WriteInt64LittleEndian(b.AsSpan(40,8),long.MaxValue),
 b=>BinaryPrimitives.WriteInt64LittleEndian(b.AsSpan(48,8),1_000_000_000),
 b=>BinaryPrimitives.WriteInt64LittleEndian(b.AsSpan(60,8),-1)}){
 MetadataTestHooks.AfterBulk=mutate;
 try{using var b=new DarwinMetadataBatch(groups,500000,ValidatePath);Require(!b.TryGet(files[0],parent,default,out _),"malformed record admitted");}
 finally{MetadataTestHooks.AfterBulk=null;}
}
foreach(var budget in new long[]{0,1,16,64}){using var b=new DarwinMetadataBatch(groups,budget,ValidatePath);b.TryGet(files[0],parent,default,out _);Require(b.Entries<=budget,"global entry budget exceeded");}
for(var i=0;i<600;i++)File.WriteAllText(Path.Combine(parent,$"unrelated-{i}.txt"),"");
using(var b=new DarwinMetadataBatch(groups,500000,ValidatePath)){foreach(var file in files)if(b.TryGet(file,parent,default,out var data))Equal(file,data);Require(b.Entries<=64*2+256,"directory amplification exceeded");}
var mode=File.GetUnixFileMode(parent);
try{File.SetUnixFileMode(parent,UnixFileMode.UserExecute);using var b=new DarwinMetadataBatch(groups,500000,ValidatePath);Require(!b.TryGet(files[0],parent,default,out _),"unreadable directory did not fall back");Require(new FileInfo(files[0]).Exists,"fallback fixture not searchable");}
finally{File.SetUnixFileMode(parent,mode);}
var descriptors=Directory.EnumerateFileSystemEntries("/dev/fd").Count();
for(var i=0;i<100;i++){using var b=new DarwinMetadataBatch(groups,500000,ValidatePath);b.TryGet(files[0],parent,default,out _);}
Require(Directory.EnumerateFileSystemEntries("/dev/fd").Count()==descriptors,"descriptor leak");
Console.WriteLine("Native metadata, unicode/negative timestamps, mutation, symlink/missing fallback, directory replacement, cancellation, malformed records, bounded enumeration, permissions and descriptor lifetime passed.");
if(args.Length>0){
 validationRoot=args[0];
 var sources=Directory.EnumerateFiles(args[0],"*.cs",SearchOption.AllDirectories).Where(p=>!p.Contains("/obj/")).ToArray();
 var graph=sources.GroupBy(p=>Path.GetDirectoryName(p)!).ToDictionary(g=>g.Key,g=>g.ToDictionary(p=>Path.GetFileName(p)!,p=>p,StringComparer.Ordinal),StringComparer.Ordinal);
 var samples=new List<object>();
 for(var iteration=0;iteration<110;iteration++){
  MetadataTestHooks.Timings.Clear();var allocation=GC.GetTotalAllocatedBytes(true);var start=System.Diagnostics.Stopwatch.GetTimestamp();
  using var b=new DarwinMetadataBatch(graph,500000,ValidatePath);
  foreach(var group in graph)foreach(var file in group.Value.Values)Require(b.TryGet(file,group.Key,default,out _),"profile fallback");
  Require(b.RetainedHandles<=64,"handle budget exceeded");
  samples.Add(new{iteration,warmup=iteration<10,ms=System.Diagnostics.Stopwatch.GetElapsedTime(start).TotalMilliseconds,allocated=GC.GetTotalAllocatedBytes(true)-allocation,b.Calls,b.Entries,b.Hits,stages=new Dictionary<string,double>(MetadataTestHooks.Timings)});
 }
 File.WriteAllText(Path.Combine(AppContext.BaseDirectory,"helper-profile.json"),System.Text.Json.JsonSerializer.Serialize(samples));
}

''')
env=dict(os.environ,DOTNET_ROOT=str(pathlib.Path(sdk).resolve().parent),DOTNET_CLI_USE_MSBUILD_SERVER='0')
subprocess.run([sdk,'build',str(out/'Proof.csproj'),'--disable-build-servers','-c','Release'],cwd=out,env=env,check=True)
subprocess.run([sdk,str(out/'bin/Release/net11.0/Proof.dll'),*([os.environ['FREEFLIGHT_METADATA_PROFILE_FIXTURE']] if os.environ.get('FREEFLIGHT_METADATA_PROFILE_FIXTURE') else [])],cwd=out,env=env,check=True)
(out/'result.json').write_text(json.dumps({'status':'passed','source':str(source),'testOnlyHooks':True},indent=2)+'\n')

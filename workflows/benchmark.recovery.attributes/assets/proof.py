# SPDX-License-Identifier: Apache-2.0
"""Fresh macOS attribute equivalence/fault/allocation proof before worker screening."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
repo=Path.cwd();label=os.environ['FREEFLIGHT_ATTRIBUTE_LABEL'];assert label and all(c.isalnum() or c in '-_' for c in label)
out=repo/'bin/.local/benchmarks/attributes'/label;out.mkdir(parents=True,exist_ok=False)
s=(repo/'workers/roslyn/Program.cs').read_text();helper=s[s.index('internal static class DarwinPathAttributes'):];(out/'original-helper.cs.txt').write_text(helper)
s=helper.replace('extern int PathAttributes(', 'extern int RealAttributes(')
anchor='    internal static FileAttributes ReadReparseFlag(string path)';assert s.count(anchor)==1
wrapper=r'''
    private static int PathAttributes(string path,ref Attributes attrs,ref byte buffer,nuint size,ulong options)
    {
        Probe.Calls++;Probe.LastOptions=options;
        if(size!=28 || attrs.Count!=5 || attrs.Common!=0x80000008)throw new Exception("Native attribute ABI changed");
        if(Probe.Mode=="failure")return -1;
        var result=RealAttributes(path,ref attrs,ref buffer,size,options);
        var data=MemoryMarshal.CreateSpan(ref buffer,28);
        void Set(int offset,uint value)=>System.Buffers.Binary.BinaryPrimitives.WriteUInt32LittleEndian(MemoryMarshal.CreateSpan(ref buffer,28)[offset..],value);
        if(result==0)
        {
            switch(Probe.Mode)
            {
                case "short":System.Buffers.Binary.BinaryPrimitives.WriteUInt32LittleEndian(data,24);break;
                case "oversized":System.Buffers.Binary.BinaryPrimitives.WriteUInt32LittleEndian(data,32);break;
                case "missing-type":System.Buffers.Binary.BinaryPrimitives.WriteUInt32LittleEndian(data[4..],0x80000000);break;
                case "extra-common":System.Buffers.Binary.BinaryPrimitives.WriteUInt32LittleEndian(data[4..],0x80000009);break;
                case "extra-group":System.Buffers.Binary.BinaryPrimitives.WriteUInt32LittleEndian(data[8..],1);break;
                case "invalid-type":System.Buffers.Binary.BinaryPrimitives.WriteUInt32LittleEndian(data[24..],0);break;
                case "unknown-type":System.Buffers.Binary.BinaryPrimitives.WriteUInt32LittleEndian(data[24..],99);break;
            }
        }
        return result;
    }
'''.replace('        void Set(int offset,uint value)=>System.Buffers.Binary.BinaryPrimitives.WriteUInt32LittleEndian(MemoryMarshal.CreateSpan(ref buffer,28)[offset..],value);\n','')
s=s.replace(anchor,wrapper+anchor).replace('if (OperatingSystem.IsMacOS())','if (!Probe.Portable && OperatingSystem.IsMacOS())').replace('        return File.GetAttributes(path);','        Probe.Fallbacks++;Probe.BeforeFallback?.Invoke();\n        return File.GetAttributes(path);')
(out/'Helper.cs').write_text('using System.Runtime.InteropServices;\n'+s)
(out/'Proof.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net11.0</TargetFramework><OutputType>Exe</OutputType><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup></Project>')
(out/'global.json').write_bytes((repo/'global.json').read_bytes())
(out/'Program.cs').write_text(r'''
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text.Json;
var root=Path.Combine(AppContext.BaseDirectory,"fixture");Directory.CreateDirectory(root);
var file=Path.Combine(root,"ordinary.cs");File.WriteAllText(file,"content");
var unicode=Path.Combine(root,"λ Café 🚀.cs");File.WriteAllText(unicode,"unicode");
var missing=Path.Combine(root,"missing.cs");var link=Path.Combine(root,"link.cs");File.CreateSymbolicLink(link,file);
var dangling=Path.Combine(root,"dangling.cs");File.CreateSymbolicLink(dangling,missing);
var directory=Path.Combine(root,"dir");Directory.CreateDirectory(directory);
var longDir=Path.Combine(root,new string('x',180));Directory.CreateDirectory(longDir);var longFile=Path.Combine(longDir,"leaf.cs");File.WriteAllText(longFile,"long");
var fifo=Path.Combine(root,"pipe.cs");if(Native.Mkfifo(fifo,384)!=0)throw new Exception("mkfifo");
int checks=0;
string Observe(string path,bool native)
{
    try{return ((native?DarwinPathAttributes.ReadReparseFlag(path):File.GetAttributes(path))&FileAttributes.ReparsePoint).ToString();}
    catch(Exception e){return e.GetType().Name+":"+e.Message;}
}
void Compare(string path,string label)
{
    var expected=Observe(path,false);var actual=Observe(path,true);
    if(expected!=actual)throw new Exception("Attribute mismatch: "+label+" "+expected+" "+actual);
    checks++;Console.WriteLine(label+": "+actual);
}
Compare(file,"regular");if(Probe.Fallbacks!=0)throw new Exception("Native fast path did not activate");
foreach(var path in new[]{file,unicode,missing,link,dangling,directory,longFile,fifo})Compare(path,"native "+Path.GetFileName(path));
if(Probe.LastOptions!=9)throw new Exception("NOFOLLOW or validity packing missing");
foreach(var mode in new[]{"failure","short","oversized","missing-type","extra-common","extra-group","invalid-type","unknown-type"})
{
    Probe.Mode=mode;var before=Probe.Fallbacks;Compare(file,"fallback "+mode);Compare(link,"fallback link "+mode);
    if(Probe.Fallbacks!=before+2)throw new Exception("Invalid metadata did not use fresh original authority: "+mode);
}
Probe.Mode="failure";Probe.BeforeFallback=()=>{File.Delete(file);File.CreateSymbolicLink(file,unicode);};if((DarwinPathAttributes.ReadReparseFlag(file)&FileAttributes.ReparsePoint)==0)throw new Exception("Fallback reused stale attributes");checks++;Console.WriteLine("replacement before fallback: fresh symlink rejected");Probe.BeforeFallback=null;
File.Delete(file);File.WriteAllText(file,"restored");Probe.Mode="";
Compare(file,"fresh regular");File.Delete(file);File.CreateSymbolicLink(file,unicode);Compare(file,"fresh symlink");File.Delete(file);File.WriteAllText(file,"restored");
Probe.Portable=true;var calls=Probe.Calls;Compare(file,"portable original");Compare(link,"portable link");if(Probe.Calls!=calls)throw new Exception("Portable fallback invoked native API");Probe.Portable=false;
for(int i=0;i<500;i++){DarwinPathAttributes.ReadReparseFlag(file);File.GetAttributes(file);}
long Alloc(bool native)
{
    var before=GC.GetAllocatedBytesForCurrentThread();
    for(int i=0;i<2000;i++){if(native)DarwinPathAttributes.ReadReparseFlag(file);else File.GetAttributes(file);}
    return GC.GetAllocatedBytesForCurrentThread()-before;
}
var nativeBytes=Alloc(true);var originalBytes=Alloc(false);if(nativeBytes>=originalBytes/4)throw new Exception("No substantial managed allocation reduction");
Console.WriteLine(JsonSerializer.Serialize(new{status="passed",checks,nativeBytes,originalBytes,iterations=2000,nativeCalls=Probe.Calls,fallbacks=Probe.Fallbacks}));
internal static class Probe {internal static string Mode="";internal static bool Portable;internal static int Calls,Fallbacks;internal static ulong LastOptions;internal static Action? BeforeFallback;}
internal static class Native{[DllImport("libc",EntryPoint="mkfifo")]internal static extern int Mkfifo(string path,uint mode);}
''')
dotnet=shutil.which('dotnet');assert dotnet
for args,name in [([dotnet,'build',str(out/'Proof.csproj'),'-c','Release','--disable-build-servers','--artifacts-path',str(out/'build')],'build.log'),([dotnet,str(out/'build/bin/Proof/release/Proof.dll')],'result.log')]:
 with (out/name).open('w') as log:subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
result=json.loads((out/'result.log').read_text().splitlines()[-1]);result['helperSha256']=hashlib.sha256(helper.encode()).hexdigest();(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');shutil.copy2(__file__,out/'adapter-source.py');print(json.dumps(result),flush=True)

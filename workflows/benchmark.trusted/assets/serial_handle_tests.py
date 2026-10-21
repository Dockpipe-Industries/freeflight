# SPDX-License-Identifier: Apache-2.0
import hashlib,json,os,pathlib,shutil,subprocess,sys
if len(sys.argv)==4:
 sdk,source,output=sys.argv[1:];root=pathlib.Path(source);out=pathlib.Path(output)
else:
 root=pathlib.Path.cwd();sdk=shutil.which('dotnet');assert sdk
 label=os.environ.get('FREEFLIGHT_SERIAL_HANDLE_LABEL','serial-proof-v1')
 assert label and all(c.isalnum() or c in '-_' for c in label)
 out=root/'bin/.local/benchmarks/serial-handles'/label
out.mkdir(parents=True,exist_ok=False)
helper=(root/'workers/roslyn/DarwinSourceHandle.cs').read_text()
source=(root/'workers/roslyn/Program.cs').read_text()
injected=helper.replace('extern int NativeOpen(', 'extern int RealOpen(').replace('extern int DescriptorAttributes(', 'extern int RealAttributes(')
anchor='    internal static FileStream Open('
injected=injected.replace(anchor,'''    internal static Action? BeforeOpen, AfterOpen;
    internal static bool FailMetadata;
    internal static int LastFd = -1, Calls;
    internal static SafeFileHandle? LastHandle;
    private static int NativeOpen(string path, int flags) { Calls++; LastHandle=null; BeforeOpen?.Invoke(); var fd=RealOpen(path, flags); LastFd=fd; AfterOpen?.Invoke(); return fd; }
    private static int DescriptorAttributes(SafeFileHandle fd, ref Attributes attrs, byte[] data, nuint size, ulong options) { LastHandle=fd; return FailMetadata ? -1 : RealAttributes(fd, ref attrs, data, size, options); }
'''+anchor)
(out/'DarwinSourceHandle.cs').write_text(injected)
check=source[source.index('    private string CheckPath(string path, HashSet<string>?'):source.index('    private static string ResolveRoot')]
(out/'Fallback.cs').write_text('''sealed class Original(string root) {
private const StringComparison PathComparison=StringComparison.Ordinal;
internal int Calls;
internal FileStream Open(string path) { Calls++; CheckPath(path,null,null); return new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete); }
'''+check+'}\n')
(out/'Proof.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net11.0</TargetFramework><OutputType>Exe</OutputType><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup></Project>')
(out/'global.json').write_bytes((root/'global.json').read_bytes())
(out/'Program.cs').write_text(r'''using FreeFlight.Roslyn;
using System.Runtime.InteropServices;
var root=Path.Combine(AppContext.BaseDirectory,"fixture");Directory.CreateDirectory(root);
var path=Path.Combine(root,"file.cs");File.WriteAllText(path,"old");var old=new Original(root);
void Assert(bool yes,string why){if(!yes)throw new Exception(why);}
void Closed(){if(DarwinSourceHandle.LastHandle is {} handle)Assert(handle.IsClosed,"owned handle leaked");}
void Reset(){DarwinSourceHandle.BeforeOpen=null;DarwinSourceHandle.AfterOpen=null;DarwinSourceHandle.FailMetadata=false;}
void Reject(string name,Action action){try{action();throw new Exception("accepted "+name);}catch(Exception e)when(e is IOException or UnauthorizedAccessException or OperationCanceledException){Closed();Console.WriteLine(name+":"+e.GetType().Name);}}
using(var stream=DarwinSourceHandle.Open(path,root,()=>old.Open(path))){Assert(stream.ReadByte()==(byte)'o',"bytes");Assert(old.Calls==0,"regular fallback hides broken fast path");}
Closed();Console.WriteLine("regular fast path and close");
DarwinSourceHandle.FailMetadata=true;
using(var stream=DarwinSourceHandle.Open(path,root,()=>old.Open(path))){Assert(stream.ReadByte()==(byte)'o',"fallback bytes");}
Closed();Assert(old.Calls==1,"unsupported metadata fallback");Reset();Console.WriteLine("metadata fallback");
DarwinSourceHandle.FailMetadata=true;
Reject("fallback failure closes original handle",()=>DarwinSourceHandle.Open(path,root,()=>throw new IOException("injected fallback")));Reset();
var outside=Path.Combine(AppContext.BaseDirectory,"outside");Directory.CreateDirectory(outside);File.WriteAllText(Path.Combine(outside,"file.cs"),"outside");
Reject("lexical escape",()=>DarwinSourceHandle.Open(Path.Combine(outside,"file.cs"),root,()=>throw new Exception("fallback on escape")));
var link=Path.Combine(root,"link.cs");File.CreateSymbolicLink(link,path);
Reject("leaf symlink",()=>DarwinSourceHandle.Open(link,root,()=>old.Open(link)));
var dir=Path.Combine(root,"ancestor");Directory.CreateSymbolicLink(dir,outside);
Reject("ancestor symlink",()=>DarwinSourceHandle.Open(Path.Combine(dir,"file.cs"),root,()=>old.Open(Path.Combine(dir,"file.cs"))));
var missing=Path.Combine(root,"missing.cs");Reject("missing error fallback",()=>DarwinSourceHandle.Open(missing,root,()=>old.Open(missing)));
var folder=Path.Combine(root,"directory.cs");Directory.CreateDirectory(folder);Reject("directory",()=>DarwinSourceHandle.Open(folder,root,()=>old.Open(folder)));
var fifo=Path.Combine(root,"fifo.cs");Assert(Native.Mkfifo(fifo,384)==0,"mkfifo");Reject("fifo no fallback",()=>DarwinSourceHandle.Open(fifo,root,()=>throw new Exception("FIFO fallback")));
var replacement=Path.Combine(root,"replacement.cs");File.WriteAllText(replacement,"old");
DarwinSourceHandle.BeforeOpen=()=>{File.Delete(replacement);File.CreateSymbolicLink(replacement,Path.Combine(outside,"file.cs"));};
Reject("before-open symlink replacement",()=>DarwinSourceHandle.Open(replacement,root,()=>old.Open(replacement)));Reset();
var regular=Path.Combine(root,"same.cs");File.WriteAllText(regular,"old");var time=File.GetLastWriteTimeUtc(regular);
DarwinSourceHandle.BeforeOpen=()=>{File.WriteAllText(regular,"new");File.SetLastWriteTimeUtc(regular,time);};
using(var stream=DarwinSourceHandle.Open(regular,root,()=>old.Open(regular))){Assert(new StreamReader(stream).ReadToEnd()=="new","restored time edit");}Closed();Reset();Console.WriteLine("restored timestamp bytes");
using(var cts=new CancellationTokenSource()){
 DarwinSourceHandle.AfterOpen=cts.Cancel;
 Reject("caller cancellation disposes handle",()=>{using var stream=DarwinSourceHandle.Open(path,root,()=>old.Open(path));cts.Token.ThrowIfCancellationRequested();});Reset();
}
var before=DarwinSourceHandle.Calls;
Reject("ordered early failure avoids later open",()=>{if(new FileInfo(path).Length>1)throw new IOException("first size failure");using var stream=DarwinSourceHandle.Open(fifo,root,()=>old.Open(fifo));});Assert(before==DarwinSourceHandle.Calls,"opened later file");
Console.WriteLine("SERIAL_HANDLE_PROOF_PASSED");
static class Native {
[DllImport("libc",EntryPoint="fcntl",SetLastError=true)]internal static extern int Fcntl(int fd,int command);
[DllImport("libc",EntryPoint="mkfifo",SetLastError=true)]internal static extern int Mkfifo(string path,uint mode);
}
''')
with (out/'output.log').open('w') as log:
 subprocess.run([sdk,'run','--project',str(out/'Proof.csproj'),'-c','Release','--disable-build-servers'],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
text=(out/'output.log').read_text();assert 'SERIAL_HANDLE_PROOF_PASSED' in text
(out/'result.json').write_text(json.dumps(dict(status='passed',helperSha256=hashlib.sha256(helper.encode()).hexdigest(),programSha256=hashlib.sha256(source.encode()).hexdigest(),output=text),indent=2)+'\n');print(text)

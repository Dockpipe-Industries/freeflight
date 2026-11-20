# SPDX-License-Identifier: Apache-2.0
"""DockPipe proof asset: pinned runtime IL and bounded read/cancellation semantics."""
import hashlib,json,os,pathlib,shutil,subprocess,sys,platform
if len(sys.argv)==1:
 root=pathlib.Path.cwd();label=os.environ['FREEFLIGHT_EXPIRY_LABEL'];assert label and all(c.isalnum() or c in '-_' for c in label)
 out=root/'bin/.local'/('expiry-proof-'+label);sdk=shutil.which('dotnet')
else:
 sdk,source,output=sys.argv[1:4];root=pathlib.Path(source);out=pathlib.Path(output)
assert platform.system()=='Darwin', 'Pinned read-scheduling proof requires Darwin'
out.mkdir(parents=True,exist_ok=False);assert sdk
source=(root/'workers/roslyn/Program.cs').read_text()
start=source.index('    private static ValueTask<int> ReadCompilerBytes(')
end=source.index('\n    }',start)+6
helper=source[start:end].replace('private static','internal static',1)
project='<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net11.0</TargetFramework><OutputType>Exe</OutputType><ImplicitUsings>enable</ImplicitUsings></PropertyGroup></Project>'
def run(name,program,extra=None):
 d=out/name;d.mkdir();(d/'Proof.csproj').write_text(project);(d/'global.json').write_bytes((root/'global.json').read_bytes());(d/'Program.cs').write_text(program)
 if extra:(d/'Reader.cs').write_text('internal static class Reader {\n'+extra+'\n}')
 with (d/'output.log').open('w') as log:subprocess.run([sdk,'run','--project',str(d/'Proof.csproj'),'-c','Release','--disable-build-servers'],cwd=d,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
 return (d/'output.log').read_text()
il=run('runtime',r'''using System.Reflection;
using System.Reflection.Emit;
var opcodes=typeof(OpCodes).GetFields().Where(f=>f.FieldType==typeof(OpCode)).Select(f=>(OpCode)f.GetValue(null)!).ToDictionary(o=>(ushort)o.Value);
var assembly=typeof(FileStream).Assembly;
Console.WriteLine(assembly.Location);
foreach(var type in assembly.GetTypes().Where(t=>t.FullName!.Contains("FileStreamStrategy") || t.FullName.Contains("AsyncOverSync") || t.FullName.Contains("AsyncReadWriteTask") || t.FullName.Contains("RandomAccess") || t.FullName.Contains("ThreadPoolValueTaskSource")))
foreach(var method in type.GetMethods(BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance|BindingFlags.Static|BindingFlags.DeclaredOnly).Where(m=>m.Name.Contains("Read") || m.Name.Contains("Invoke") || m.Name.Contains("Execute") || m.Name=="MoveNext" || m.Name.Contains("Queue"))){
 var body=method.GetMethodBody()?.GetILAsByteArray();if(body==null)continue;
 Console.WriteLine("METHOD "+type.FullName+"."+method);
 for(int i=0;i<body.Length;){int start=i;ushort code=body[i++];if(code==0xfe)code=(ushort)(0xfe00|body[i++]);var op=opcodes[code];int n=op.OperandType switch {OperandType.InlineNone=>0,OperandType.ShortInlineBrTarget or OperandType.ShortInlineI or OperandType.ShortInlineVar=>1,OperandType.InlineVar=>2,OperandType.InlineI8 or OperandType.InlineR=>8,OperandType.InlineSwitch=>4+4*BitConverter.ToInt32(body,i),_=>4};string arg="";if(op.OperandType==OperandType.InlineMethod){try{arg=method.Module.ResolveMethod(BitConverter.ToInt32(body,i),type.IsGenericType?type.GetGenericArguments():null,method.IsGenericMethod?method.GetGenericArguments():null)!.ToString();}catch{arg="unresolved";}}else if(n>0)arg=Convert.ToHexString(body.AsSpan(i,n));Console.WriteLine($" {start:x4} {op.Name} {arg}");i+=n;}
}
''')
assert 'ThreadPoolValueTaskSource.Void ExecuteInternal()' in il
assert 'ReadAtOffset(' in il and 'get_IsCancellationRequested()' in il
result=run('semantics',r'''
var directory=Path.Combine(AppContext.BaseDirectory,"fixture");Directory.CreateDirectory(directory);
var file=Path.Combine(directory,"content");var original=Enumerable.Range(0,32781).Select(i=>(byte)(i%251)).ToArray();File.WriteAllBytes(file,original);
void Require(bool condition,string message){if(!condition)throw new Exception(message);}
foreach(var inline in new[]{false,true}){
 using var stream=new FileStream(file,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete);using var received=new MemoryStream();var buffer=new byte[8192];int count;
 while((count=await Reader.ReadCompilerBytes(stream,buffer,default,inline))!=0)received.Write(buffer,0,count);
 Require(original.SequenceEqual(received.ToArray()),"bytes/EOF changed");
}
using(var cts=new CancellationTokenSource())using(var stream=new Probe(file)){
 cts.Cancel();bool cancelled=false;try{await Reader.ReadCompilerBytes(stream,new byte[8192],cts.Token,true);}catch(OperationCanceledException){cancelled=true;}
 Require(cancelled && stream.Reads==0,"pre-cancel performed read");
}
using(var cts=new CancellationTokenSource())using(var stream=new Probe(file)){
 stream.AfterRead=cts.Cancel;var buffer=new byte[8192];var count=await Reader.ReadCompilerBytes(stream,buffer,cts.Token,true);
 Require(count==8192 && stream.Reads==1,"in-flight read changed result");using var memory=new MemoryStream();bool cancelled=false;
 try{await memory.WriteAsync(buffer.AsMemory(0,count),cts.Token);}catch(OperationCanceledException){cancelled=true;}
 Require(cancelled && memory.Length==0,"post-read cancellation lost");
}
using(var cts=new CancellationTokenSource())using(var stream=new Probe(file)){
 stream.BeforeRead=()=>{cts.Cancel();throw new IOException("injected read failure");};bool failed=false;
 try{await Reader.ReadCompilerBytes(stream,new byte[8192],cts.Token,true);}catch(IOException e){failed=e.Message=="injected read failure";}
 Require(failed,"I/O error order changed");
}
using(var cts=new CancellationTokenSource())using(var stream=new Probe(file)){
 stream.AfterRead=()=>{if(stream.Reads==3)cts.Cancel();};var buffer=new byte[8192];bool cancelled=false;
 try{while(await Reader.ReadCompilerBytes(stream,buffer,cts.Token,true)!=0){}}catch(OperationCanceledException){cancelled=true;}
 Require(cancelled && stream.Reads==3,"read cancellation boundary changed");
}
using(var stream=new Probe(file)){
 var count=await Reader.ReadCompilerBytes(stream,new byte[8192],default,false);
 Require(count==8192 && stream.AsyncReads==1,"fallback skipped async API");
}
Console.WriteLine("Exact bytes, EOF, pre-read cancellation, in-flight completion, subsequent cancellation, I/O failure precedence and async fallback passed.");
sealed class Probe(string path):FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete){
 internal int Reads,AsyncReads;internal Action BeforeRead,AfterRead;
 public override int Read(byte[] buffer,int offset,int count){BeforeRead?.Invoke();Reads++;var n=base.Read(buffer,offset,count);AfterRead?.Invoke();return n;}
 public override ValueTask<int> ReadAsync(Memory<byte> buffer,CancellationToken token=default){AsyncReads++;return base.ReadAsync(buffer,token);}
}
''',helper)
corelib=pathlib.Path(il.splitlines()[0])
corelib_hash=hashlib.sha256(corelib.read_bytes()).hexdigest()
assert corelib_hash=='efbd28e6caa106316440b0793d31d51352f132f15de0e358ef7e7f81f2ac4781', 'Re-review read cancellation IL for this changed runtime before qualifying inline reads'
receipt=dict(status='passed',sourceSha256=hashlib.sha256(source.encode()).hexdigest(),corelib=str(corelib),corelibSha256=corelib_hash,sdk=subprocess.check_output([sdk,'--version']).decode().strip(),note='IL inspection is runtime-specific; no universal runtime cancellation claim',result=result)
(out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n');print(result)

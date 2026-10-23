# SPDX-License-Identifier: Apache-2.0
"""Compare cached lexical paths to the unchanged uncached checker and live attributes."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
repo=Path.cwd();receipt=repo/'bin/.local/benchmarks/trusted'/os.environ['FREEFLIGHT_PATH_RECEIPT'];c=json.loads((receipt/'provenance.json').read_text());out=receipt/'lexical-proof';out.mkdir(exist_ok=False);source=out/'source';shutil.copytree(receipt/'candidate/source',source)
p=source/'workers/roslyn/Program.cs';assert hashlib.sha256(p.read_bytes()).hexdigest()==c['variants']['candidate']['sourceHashes']['workers/roslyn/Program.cs'];s=p.read_text();assert 'trustedValidationParents' in s;s=s.replace('File.GetAttributes(', 'PathProbe.Attributes(');p.write_text(s)
(source/'workers/roslyn/PathProof.cs').write_text(r'''
using System.Reflection;
namespace FreeFlight.Roslyn;
internal static class PathProbe
{
    internal static readonly List<string> Seen=new();
    internal static FileAttributes Attributes(string path){Seen.Add(path);return File.GetAttributes(path);}
}
internal static class PathProof
{
    public static void Main()
    {
        var root=Path.Combine(AppContext.BaseDirectory,"fixture");Directory.CreateDirectory(Path.Combine(root,"nested"));
        var first=Path.Combine(root,"nested","first.cs");var second=Path.Combine(root,"nested","second.cs");
        File.WriteAllText(first,"old");File.WriteAllText(second,"second");
        using var engine=new SourceEngine(true);
        var type=typeof(SourceEngine);const BindingFlags flags=BindingFlags.NonPublic|BindingFlags.Instance;
        type.GetField("root",flags)!.SetValue(engine,root);
        var paths=(List<FileInfo>)type.GetField("trustedPaths",flags)!.GetValue(engine)!;
        paths.Add(new(first));paths.Add(new(second));
        type.GetMethod("BuildTrustedValidationParents",flags)!.Invoke(engine,null);
        var plans=(Dictionary<string,string[]>)type.GetField("trustedValidationParents",flags)!.GetValue(engine)!;
        var cached=type.GetMethod("CheckPath",flags,null,new[]{typeof(string)},null)!;
        var uncached=type.GetMethod("CheckPath",flags,null,new[]{typeof(string),typeof(HashSet<string>),typeof(FileInfo)},null)!;
        int checks=0;
        (string,List<string>) Observe(string path,bool fast)
        {
            PathProbe.Seen.Clear();string result;
            try {result="ok:"+(string)(fast?cached.Invoke(engine,new object?[]{path}):uncached.Invoke(engine,new object?[]{path,null,null}))!;}
            catch(TargetInvocationException e){result=e.InnerException!.GetType().Name+":"+e.InnerException.Message;}
            return(result,new(PathProbe.Seen));
        }
        void Compare(string path,string label,bool reject=false)
        {
            var a=Observe(path,false);var b=Observe(path,true);
            if(a.Item1!=b.Item1 || !a.Item2.SequenceEqual(b.Item2) || (reject && b.Item1.StartsWith("ok:")))
                throw new Exception("Checker mismatch: "+label+" "+a.Item1+" "+b.Item1);
            checks++;Console.WriteLine(label+": fresh attribute order equal ("+b.Item2.Count+")");
        }
        if(plans.Count!=2 || !ReferenceEquals(plans[first],plans[second]))throw new Exception("Lexical catalogue is not graph-bound/shared");
        Compare(first,"first canonical read");Compare(first,"repeated canonical read");Compare(second,"shared parent read");
        Compare("nested/first.cs","relative request");Compare(Path.Combine(root,"nested","..","nested","first.cs"),"alternate lexical spelling");
        Compare(Path.Combine(root,"..","escape.cs"),"escape rejected",true);
        Compare(Path.Combine(root,"missing.cs"),"unknown path rejected",true);
        File.Delete(first);Compare(first,"cached missing leaf rejected",true);
        File.CreateSymbolicLink(first,second);Compare(first,"cached leaf symlink rejected",true);File.Delete(first);File.WriteAllText(first,"changed");
        Compare(first,"regular replacement readmitted freshly");
        var nested=Path.Combine(root,"nested");var saved=Path.Combine(root,"saved");Directory.Move(nested,saved);Directory.CreateSymbolicLink(nested,saved);
        Compare(first,"cached ancestor symlink rejected",true);Directory.Delete(nested);Directory.Move(saved,nested);Compare(first,"ancestor restored");
        if(plans.Count!=2)throw new Exception("Requests expanded lexical catalogue");
        Console.WriteLine(System.Text.Json.JsonSerializer.Serialize(new{status="passed",checks,sharedParents=true,requestGrowth=false}));
    }
}
''')
with (out/'build.log').open('w') as log:subprocess.run([c['dotnet'],'build',str(source/'workers/roslyn/FreeFlight.Roslyn.csproj'),'-c','Release','-p:StartupObject=FreeFlight.Roslyn.PathProof','-p:RestoreLockedMode=true','--disable-build-servers','--artifacts-path',str(out/'build')],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
with (out/'result.log').open('w') as log:subprocess.run([c['dotnet'],str(out/'build/bin/FreeFlight.Roslyn/release/FreeFlight.Roslyn.dll')],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=30)
result=json.loads((out/'result.log').read_text().splitlines()[-1]);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');shutil.copy2(__file__,out/'adapter-source.py');print('Path lexical proof:',result,flush=True)

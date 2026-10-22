# SPDX-License-Identifier: Apache-2.0
"""Pinned Roslyn ownership proof for a request-local reusable source byte buffer."""
import hashlib,json,os,pathlib,subprocess
root=pathlib.Path.cwd()
receipt=root/'bin/.local/benchmarks/trusted'/os.environ['FREEFLIGHT_BUFFER_RECEIPT']
config=json.loads((receipt/'provenance.json').read_text())
out=receipt/'buffer-ownership-proof';out.mkdir(exist_ok=False)
source=receipt/'candidate/source/workers/roslyn/Program.cs'
assert hashlib.sha256(source.read_bytes()).hexdigest()==config['variants']['candidate']['sourceHashes']['workers/roslyn/Program.cs']
assert 'memory.SetLength(0);' in source.read_text()
assembly=pathlib.Path(config['variants']['candidate']['dll']).parent/'Microsoft.CodeAnalysis.dll'
assert assembly.is_file()
(out/'global.json').write_bytes((root/'global.json').read_bytes())
(out/'Proof.csproj').write_text(f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net11.0</TargetFramework><OutputType>Exe</OutputType><ImplicitUsings>enable</ImplicitUsings></PropertyGroup><ItemGroup><Reference Include="Microsoft.CodeAnalysis"><HintPath>{assembly}</HintPath></Reference></ItemGroup></Project>')
(out/'Program.cs').write_text(r'''
using System.Text;
using Microsoft.CodeAnalysis.Text;
var retained = new List<(SourceText text, string expected, byte[] checksum)>();
using (var memory = new MemoryStream()) {
  foreach (var length in new[] { 1000000, 0, 1, 8191, 8192, 8193, 90000, 2, 4096 }) {
    var value = new string('x', length) + "\n\u03bb\u65e5\U0001f680\r\n";
    var bytes = Encoding.UTF8.GetBytes(value);
    memory.SetLength(0); memory.Position = 0;
    for (var offset=0;offset<bytes.Length;offset+=8192)
      await memory.WriteAsync(bytes.AsMemory(offset,Math.Min(8192,bytes.Length-offset)));
    memory.Position = 0;
    var text = SourceText.From(memory, encoding: Encoding.UTF8);
    using var oracle = new MemoryStream(bytes);
    var reference = SourceText.From(oracle, encoding: Encoding.UTF8);
    if (text.ToString()!=value || !text.GetChecksum().SequenceEqual(reference.GetChecksum()))
      throw new Exception("Fresh text/checksum or prior suffix changed");
    retained.Add((text,value,reference.GetChecksum().ToArray()));
    Array.Fill(memory.GetBuffer(), (byte)0x7f);
    foreach (var item in retained)
      if (item.text.ToString()!=item.expected || !item.text.GetChecksum().SequenceEqual(item.checksum))
        throw new Exception("SourceText retained reusable bytes");
  }
}
foreach (var item in retained)
  if (item.text.ToString()!=item.expected || !item.text.GetChecksum().SequenceEqual(item.checksum))
    throw new Exception("Disposed buffer changed retained text");
Console.WriteLine("Passed nine descending/ascending/chunk-boundary Unicode inputs, overwrite and dispose ownership checks.");
''')
with (out/'output.log').open('w') as log:
 subprocess.run([config['dotnet'],'run','--project',str(out/'Proof.csproj'),'-c','Release','--disable-build-servers'],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
result=dict(status='passed',workerSourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),roslynAssemblySha256=hashlib.sha256(assembly.read_bytes()).hexdigest(),sdk=config['sdk'],output=(out/'output.log').read_text())
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(result['output'])

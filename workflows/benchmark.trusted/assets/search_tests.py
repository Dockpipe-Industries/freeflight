# SPDX-License-Identifier: Apache-2.0
"""Differential oracle: unchanged d8232ec search against the candidate Roslyn API path."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

dotnet, source, destination = sys.argv[1:]
out = Path(destination)
out.mkdir(parents=True, exist_ok=False)
copy = out / 'source'
shutil.copytree(source, copy)
repo = Path(__file__).resolve().parents[3]
oracle = subprocess.check_output(['git', 'show', 'd8232ec:workers/roslyn/SemanticQueries.cs'], cwd=repo)
(copy / 'workers/roslyn/SearchOracle.cs').write_text(oracle.decode().replace('internal static class SemanticQueries', 'internal static class SearchOracle'))
(copy / 'workers/roslyn/SearchProof.cs').write_text(r'''
using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.Text;
namespace FreeFlight.Roslyn;
internal static class SearchProof
{
    public static async Task Main()
    {
        using var workspace = new AdhocWorkspace();
        var references = ((string)AppContext.GetData("TRUSTED_PLATFORM_ASSEMBLIES")!).Split(Path.PathSeparator)
            .Select(path => MetadataReference.CreateFromFile(path)).ToArray();
        var solution = workspace.CurrentSolution;
        var ids = new List<ProjectId>();
        for (var i = 0; i < 3; i++)
        {
            var id = ProjectId.CreateNewId();
            ids.Add(id);
            solution = solution.AddProject(ProjectInfo.Create(id, VersionStamp.Create(), "P" + i, "P" + i,
                LanguageNames.CSharp, compilationOptions: new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary),
                parseOptions: new CSharpParseOptions(LanguageVersion.Preview), metadataReferences: references));
        }
        solution = solution.AddProjectReference(ids[1], new ProjectReference(ids[0]));
        var source = """
            namespace Example;
            public interface IContract { int Value { get; } void Run(); }
            public partial class Container<T> : IContract where T : class
            {
                public Container() { }
                public int Field;
                public const int Constant = 1;
                public int Value { get; private set; }
                public int this[int position] => position;
                public event System.Action? Changed;
                public event System.Action ExplicitEvent { add { } remove { } }
                void IContract.Run() { }
                public void Run() { System.Action action = () => { }; action(); }
                public void Run(int value) { }
                public partial void Partial(int value);
                public class Nested { public int Café; public int λ; public int İ; }
                public static Container<T> operator +(Container<T> left, Container<T> right) => left;
                public static explicit operator int(Container<T> value) => 1;
                ~Container() { }
            }
            public partial class Container<T> { public partial void Partial(int value) { } }
            public record RecordType(int RecordValue);
            public record struct StructRecord(int StructValue);
            public class Primary(int PrimaryValue) { public int Read() => PrimaryValue; }
            public enum Enumeration { One, Two }
            public delegate void Callback(int item);
            """;
        var target = DocumentId.CreateNewId(ids[0]);
        solution = solution.AddDocument(target, "Declarations.cs", SourceText.From(source), filePath: "/fixture/Declarations.cs");
        solution = solution.AddDocument(DocumentId.CreateNewId(ids[1]), "Consumer.cs",
            SourceText.From("class Consumer { public Example.RecordType Make() => new(1); }"), filePath: "/fixture/Consumer.cs");
        foreach (var id in ids)
            solution = solution.AddDocument(DocumentId.CreateNewId(id), "Shared.cs",
                SourceText.From("namespace Shared; public class SharedType { public int SharedValue; }"), filePath: "/external/Shared.cs");
        if (solution.Projects.Any(project => project.TryGetCompilation(out _)))
            throw new Exception("Cold fixture unexpectedly compiled");
        await SemanticQueries.WorkspaceSymbols(solution, "NoMatch", CancellationToken.None);
        if (solution.Projects.Any(project => project.TryGetCompilation(out _)))
            throw new Exception("Negative cold search forced compilation");
        var queries = new[] { "C", "Value", "Record", "Struct", "Primary", "Run", "Partial", "Nested", "Café", "λ", "İ", "i",
            "get_", "set_", "add_", "remove_", "op_", "ctor", "Finalize", "Item", "Changed", "ExplicitEvent", "IContract.Run",
            "Shared", "System", "Int32", "NoMatch", "<", "One", "Callback", "Example", "cOnTaInEr", " ", "" };
        var checks = 0;
        async Task<string> Observe(Func<Task<object>> action)
        {
            try { return JsonSerializer.Serialize(await action()); }
            catch (Exception error) { return error.GetType().Name + ":" + error.Message; }
        }
        async Task Compare(Solution current, string query)
        {
            string expected;
            string actual;
            if (checks % 2 == 0)
            {
                actual = await Observe(() => SemanticQueries.WorkspaceSymbols(current, query, CancellationToken.None));
                expected = await Observe(() => SearchOracle.WorkspaceSymbols(current, query, CancellationToken.None));
            }
            else
            {
                expected = await Observe(() => SearchOracle.WorkspaceSymbols(current, query, CancellationToken.None));
                actual = await Observe(() => SemanticQueries.WorkspaceSymbols(current, query, CancellationToken.None));
            }
            if (expected != actual) throw new InvalidOperationException($"Oracle mismatch for '{query}': expected {expected}; actual {actual}");
            checks++;
        }
        foreach (var query in queries) await Compare(solution, query);
        solution = solution.WithDocumentText(target, SourceText.From(source.Replace("RecordValue", "ChangedName")));
        foreach (var query in queries.Append("ChangedName")) await Compare(solution, query);
        solution = solution.RemoveDocument(target);
        foreach (var query in queries) await Compare(solution, query);
        solution = solution.AddDocument(DocumentId.CreateNewId(ids[0]), "Many.cs", SourceText.From(
            string.Join("\n", Enumerable.Range(0, 1001).Select(i => "class Match" + i + " {}"))), filePath: "/fixture/Many.cs");
        await Compare(solution, "Match");
        using var cancelled = new CancellationTokenSource();
        cancelled.Cancel();
        var failure = await Observe(() => SemanticQueries.WorkspaceSymbols(solution, "Match", cancelled.Token));
        if (!failure.Contains("CanceledException")) throw new Exception("Cancellation was not observed: " + failure);
        Console.WriteLine(JsonSerializer.Serialize(new { status = "passed", checks, cancellation = true, coldMissAvoidsCompilation = true }));
    }
}
''')
# For the bounded-project candidate, exercise real task draining and project-order
# failure selection in generated source, in addition to the unchanged API oracle.
semantic = copy / 'workers/roslyn/SemanticQueries.cs'
if 'FindProjectDeclarations(' in semantic.read_text():
    text = semantic.read_text()
    old = 'SymbolFinder.FindSourceDeclarationsAsync(project, predicate, SymbolFilter.TypeAndMember, token)'
    assert text.count(old) == 1
    semantic.write_text(text.replace(old, 'SearchProbe.Query(project, predicate, token)'))
    proof = copy / 'workers/roslyn/SearchProof.cs'
    text = proof.read_text()
    old = '        Console.WriteLine(JsonSerializer.Serialize(new { status = "passed", checks, cancellation = true, coldMissAvoidsCompilation = true }));'
    assert text.count(old) == 1
    text = text.replace(old, '        await SearchProbe.Prove(solution);\n' + old)
    text += r'''
internal static class SearchProbe
{
    private static bool Enabled;
    private static string Mode = "hold";
    private static int Active, Peak, Started;
    public static async Task<IEnumerable<ISymbol>> Query(Project project, Func<string,bool> predicate, CancellationToken token)
    {
        if (!Enabled) return await Microsoft.CodeAnalysis.FindSymbols.SymbolFinder.FindSourceDeclarationsAsync(
            project,predicate,SymbolFilter.TypeAndMember,token);
        Interlocked.Increment(ref Started);
        var count=Interlocked.Increment(ref Active);
        int peak;
        while(count>(peak=Volatile.Read(ref Peak)) && Interlocked.CompareExchange(ref Peak,count,peak)!=peak) { }
        try
        {
            if(Mode=="hold") await Task.Delay(Timeout.Infinite,token);
            else { await Task.Delay(project.Name=="P0"?30:1,token); throw new InvalidOperationException(project.Name); }
            return Array.Empty<ISymbol>();
        }
        finally { Interlocked.Decrement(ref Active); }
    }
    public static async Task Prove(Solution solution)
    {
        Enabled=true;
        try
        {
            using var cancel=new CancellationTokenSource();
            var pending=SemanticQueries.WorkspaceSymbols(solution,"Value",cancel.Token);
            var deadline=DateTime.UtcNow.AddSeconds(5);
            while(Volatile.Read(ref Active)<2 && DateTime.UtcNow<deadline) await Task.Delay(1);
            cancel.Cancel();
            var cancelled=false;
            try { await pending; } catch(OperationCanceledException) { cancelled=true; }
            if(!cancelled || Active!=0 || Peak!=2 || Started!=2) throw new Exception("Bounded search did not cancel/drain exactly two tasks");
            Active=Peak=Started=0;Mode="fail";
            var error="";
            try { await SemanticQueries.WorkspaceSymbols(solution,"Value",CancellationToken.None); }
            catch(InvalidOperationException e) { error=e.Message; }
            if(error!="P0" || Active!=0 || Peak>2 || Started!=2) throw new Exception("Search failure order/drain changed: "+error);
            Console.WriteLine("Passed two-project bound, in-flight cancellation/drain, and original project failure precedence.");
        }
        finally { Enabled=false; }
    }
}
'''
    proof.write_text(text)

with (out / 'build.log').open('w') as log:
    subprocess.run([dotnet, 'build', str(copy/'workers/roslyn/FreeFlight.Roslyn.csproj'), '-c', 'Release',
                    '-p:StartupObject=FreeFlight.Roslyn.SearchProof', '--disable-build-servers',
                    '--artifacts-path', str(out/'build')], check=True, stdout=log, stderr=subprocess.STDOUT)
dll = out/'build/bin/FreeFlight.Roslyn/release/FreeFlight.Roslyn.dll'
with (out/'result.log').open('w') as log:
    subprocess.run([dotnet, str(dll)], check=True, stdout=log, stderr=subprocess.STDOUT, timeout=60)
result = json.loads((out/'result.log').read_text().splitlines()[-1])
result['oracleCommit'] = 'd8232ec49ce5e17af11b5032aedb40fd38ef0754'
result['oracleSha256'] = hashlib.sha256(oracle).hexdigest()
(out/'summary.json').write_text(json.dumps(result, indent=2))
print('Search differential proof passed:', result['checks'])

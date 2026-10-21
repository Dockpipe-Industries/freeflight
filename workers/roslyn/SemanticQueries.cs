using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.FindSymbols;
using Microsoft.CodeAnalysis.Operations;
using Microsoft.CodeAnalysis.Text;

namespace FreeFlight.Roslyn;

internal static class SemanticQueries
{
    private const int MaximumSymbols = 1000;
    private const int MaximumEdges = 500;

    public static object Location(Location location) => new
    {
        file = location.SourceTree?.FilePath,
        range = Range(location.GetLineSpan().Span)
    };

    private static object Range(LinePositionSpan span) => new
    {
        start = new { line = span.Start.Line, character = span.Start.Character },
        end = new { line = span.End.Line, character = span.End.Character }
    };

    private static object Item(ISymbol symbol) => new
    {
        name = symbol.Name,
        kind = symbol.Kind.ToString(),
        display = symbol.ToDisplayString(SymbolDisplayFormat.MinimallyQualifiedFormat),
        locations = symbol.Locations.Where(location => location.IsInSource).Select(Location).ToArray()
    };

    private static ISymbol[] Ordered(IEnumerable<ISymbol> symbols, CancellationToken token)
    {
        var result = new HashSet<ISymbol>(SymbolEqualityComparer.Default);
        foreach (var symbol in symbols)
        {
            token.ThrowIfCancellationRequested();
            result.Add(symbol);
            if (result.Count > MaximumSymbols)
                throw new InvalidOperationException("Query exceeds 1000 symbols; narrow the query");
        }
        return result.OrderBy(symbol => symbol.ToDisplayString(), StringComparer.Ordinal)
            .ThenBy(symbol => symbol.Locations.FirstOrDefault()?.SourceTree?.FilePath, StringComparer.Ordinal)
            .ThenBy(symbol => symbol.Locations.FirstOrDefault()?.SourceSpan.Start ?? 0).ToArray();
    }

    public static async Task<object> WorkspaceSymbols(Solution solution, string query, CancellationToken token)
    {
        if (query.Length is < 1 or > 256) throw new ArgumentException("query must contain 1 to 256 characters");
        var symbols = await FindCompilationDeclarations(solution, query, token);
        return Ordered(symbols, token).Where(symbol => !symbol.IsImplicitlyDeclared).Select(Item).ToArray();
    }

    // Use Roslyn-owned existing compilations without forcing a cold compilation
    // merely to bypass a per-document syntactic existence precheck.
    private static async Task<IEnumerable<ISymbol>> FindCompilationDeclarations(
        Solution solution, string query, CancellationToken token)
    {
        var result = new HashSet<ISymbol>(SymbolEqualityComparer.Default);
        foreach (var project in solution.Projects)
        {
            token.ThrowIfCancellationRequested();
            if (!project.SupportsCompilation) continue;
            IEnumerable<ISymbol>? symbols = null;
            if (project.TryGetCompilation(out var compilation) && compilation is not null)
            {
                var matches = compilation.GetSymbolsWithName(
                    name => name.Contains(query, StringComparison.OrdinalIgnoreCase), SymbolFilter.TypeAndMember, token)
                    .Where(IsSearchDeclaration).ToArray();
                // A matching ordinary declaration proves the syntactic precheck
                // true. Special compiler names without that witness fall back.
                if (matches.Length == 0 || matches.Any(symbol => HasMatchingSyntaxName(symbol, query, token)))
                    symbols = matches;
            }
            // Preserve cold/unavailable compilation behavior, including cheap
            // negative queries that the original syntax index can reject.
            symbols ??= await SymbolFinder.FindSourceDeclarationsAsync(project,
                name => name.Contains(query, StringComparison.OrdinalIgnoreCase), SymbolFilter.TypeAndMember, token);
            foreach (var symbol in symbols)
            {
                token.ThrowIfCancellationRequested();
                result.Add(symbol);
            }
        }
        return result;
    }

    private static bool IsSearchDeclaration(ISymbol symbol)
    {
        if (symbol.IsImplicitlyDeclared || symbol is IMethodSymbol
            { MethodKind: MethodKind.PropertyGet or MethodKind.PropertySet or
                MethodKind.EventAdd or MethodKind.EventRemove or MethodKind.EventRaise }) return false;
        return symbol is ITypeSymbol || symbol.Kind is
            SymbolKind.Method or SymbolKind.Property or SymbolKind.Event or SymbolKind.Field;
    }

    private static bool HasMatchingSyntaxName(ISymbol symbol, string query, CancellationToken token)
    {
        foreach (var reference in symbol.DeclaringSyntaxReferences)
        {
            token.ThrowIfCancellationRequested();
            var name = reference.GetSyntax(token) switch
            {
                BaseTypeDeclarationSyntax declaration => declaration.Identifier.ValueText,
                DelegateDeclarationSyntax declaration => declaration.Identifier.ValueText,
                MethodDeclarationSyntax declaration => declaration.Identifier.ValueText,
                PropertyDeclarationSyntax declaration => declaration.Identifier.ValueText,
                EventDeclarationSyntax declaration => declaration.Identifier.ValueText,
                VariableDeclaratorSyntax declaration => declaration.Identifier.ValueText,
                EnumMemberDeclarationSyntax declaration => declaration.Identifier.ValueText,
                _ => null
            };
            if (name is not null && name.Contains(query, StringComparison.OrdinalIgnoreCase)) return true;
        }
        return false;
    }

    public static object TypeInfo(SemanticModel model, SyntaxNode syntax, int position, ISymbol? symbol, CancellationToken token)
    {
        var node = syntax.FindToken(Math.Min(position, Math.Max(0, syntax.FullSpan.End - 1))).Parent;
        ITypeSymbol? type = symbol switch
        {
            ILocalSymbol local => local.Type,
            IParameterSymbol parameter => parameter.Type,
            IFieldSymbol field => field.Type,
            IPropertySymbol property => property.Type,
            IEventSymbol @event => @event.Type,
            IMethodSymbol method => method.ReturnType,
            ITypeSymbol named => named,
            _ => null
        };
        ITypeSymbol? converted = null;
        var expression = node?.AncestorsAndSelf().OfType<ExpressionSyntax>().FirstOrDefault();
        if (expression is not null)
        {
            var info = model.GetTypeInfo(expression, token);
            type ??= info.Type;
            converted = info.ConvertedType;
        }
        return new
        {
            display = type?.ToDisplayString(SymbolDisplayFormat.MinimallyQualifiedFormat),
            fullyQualified = type?.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat),
            convertedType = converted?.ToDisplayString(SymbolDisplayFormat.MinimallyQualifiedFormat),
            kind = type?.TypeKind.ToString(),
            nullable = type?.NullableAnnotation.ToString()
        };
    }

    public static object SignatureHelp(SemanticModel model, SyntaxNode syntax, int position, CancellationToken token)
    {
        var node = syntax.FindToken(Math.Min(position, Math.Max(0, syntax.FullSpan.End - 1))).Parent;
        var arguments = node?.AncestorsAndSelf().OfType<ArgumentListSyntax>()
            .FirstOrDefault(list => list.Span.Start <= position && position <= list.Span.End);
        if (arguments?.Parent is not InvocationExpressionSyntax invocation)
            return new { signatures = Array.Empty<object>(), argumentIndex = 0, argumentCount = 0, selectedItemIndex = -1 };
        var symbolInfo = model.GetSymbolInfo(invocation, token);
        var selected = symbolInfo.Symbol as IMethodSymbol;
        var methods = model.GetMemberGroup(invocation.Expression, token).OfType<IMethodSymbol>().Cast<ISymbol>();
        if (selected is not null) methods = methods.Append(selected);
        var ordered = Ordered(methods, token).OfType<IMethodSymbol>().ToArray();
        var index = Array.FindIndex(ordered, method => SymbolEqualityComparer.Default.Equals(method, selected));
        return new
        {
            selectedItemIndex = index,
            argumentIndex = arguments.Arguments.GetSeparators().Count(separator => separator.SpanStart < position),
            argumentCount = arguments.Arguments.Count,
            signatures = ordered.Select(method => new
            {
                display = method.ToDisplayString(SymbolDisplayFormat.MinimallyQualifiedFormat),
                documentation = method.GetDocumentationCommentXml(cancellationToken: token),
                parameters = method.Parameters.Select(parameter => new
                {
                    name = parameter.Name,
                    display = parameter.ToDisplayString(SymbolDisplayFormat.MinimallyQualifiedFormat),
                    optional = parameter.IsOptional,
                    isParams = parameter.IsParams
                }).ToArray()
            }).ToArray()
        };
    }

    public static async Task<object> Implementations(ISymbol symbol, Solution solution, CancellationToken token)
    {
        IEnumerable<ISymbol> found = await SymbolFinder.FindImplementationsAsync(symbol, solution, cancellationToken: token);
        if (symbol is INamedTypeSymbol { TypeKind: TypeKind.Class } named)
            found = found.Concat(await SymbolFinder.FindDerivedClassesAsync(named, solution, cancellationToken: token));
        else if (symbol.IsAbstract || symbol.IsVirtual || symbol.IsOverride)
            found = found.Concat(await SymbolFinder.FindOverridesAsync(symbol, solution, cancellationToken: token));
        var implementations = Ordered(found, token);
        var expanded = implementations.AsEnumerable();
        foreach (var implementation in implementations.Where(item => item.IsVirtual || item.IsAbstract || item.IsOverride))
        {
            token.ThrowIfCancellationRequested();
            expanded = expanded.Concat(await SymbolFinder.FindOverridesAsync(implementation, solution, cancellationToken: token));
        }
        return Ordered(expanded, token).Select(Item).ToArray();
    }

    public static async Task<object> TypeHierarchy(ISymbol symbol, Solution solution, CancellationToken token)
    {
        var type = symbol as INamedTypeSymbol;
        if (type is null || type.TypeKind is not (TypeKind.Class or TypeKind.Interface))
            return Array.Empty<object>();
        var parents = type.Interfaces.Cast<ISymbol>();
        if (type.BaseType is not null) parents = parents.Append(type.BaseType);
        IEnumerable<ISymbol> children;
        if (type.TypeKind == TypeKind.Interface)
        {
            var interfaces = await SymbolFinder.FindDerivedInterfacesAsync(type, solution, transitive: false, cancellationToken: token);
            var implementations = await SymbolFinder.FindImplementationsAsync(type, solution, cancellationToken: token);
            children = interfaces.Cast<ISymbol>().Concat(implementations.OfType<INamedTypeSymbol>()
                .Where(candidate => candidate.Interfaces.Any(parent => SymbolEqualityComparer.Default.Equals(parent, type))));
        }
        else
        {
            children = await SymbolFinder.FindDerivedClassesAsync(type, solution, transitive: false, cancellationToken: token);
        }
        return new { item = Item(type), supertypes = Ordered(parents, token).Select(Item).ToArray(), subtypes = Ordered(children, token).Select(Item).ToArray() };
    }

    public static async Task<object> CallHierarchy(ISymbol symbol, Solution solution, CancellationToken token)
    {
        if (symbol is not IMethodSymbol) return Array.Empty<object>();
        var callers = (await SymbolFinder.FindCallersAsync(symbol, solution, token)).ToArray();
        if (callers.Length > MaximumEdges) throw new InvalidOperationException("Call hierarchy exceeds 500 incoming edges");
        var incoming = new List<object>();
        var incomingLocations = 0;
        foreach (var caller in callers.OrderBy(caller => caller.CallingSymbol.ToDisplayString(), StringComparer.Ordinal))
        {
            token.ThrowIfCancellationRequested();
            var locations = caller.Locations.Where(location => location.IsInSource).ToArray();
            incomingLocations += locations.Length;
            if (incomingLocations > MaximumEdges) throw new InvalidOperationException("Call hierarchy exceeds 500 incoming locations");
            incoming.Add(new { from = Item(caller.CallingSymbol), isDirect = caller.IsDirect, locations = locations.Select(Location).ToArray() });
        }
        var calls = new CallWalker(token);
        foreach (var reference in symbol.DeclaringSyntaxReferences)
        {
            token.ThrowIfCancellationRequested();
            var syntax = await reference.GetSyntaxAsync(token);
            var document = solution.GetDocument(syntax.SyntaxTree);
            if (document is null) continue;
            var model = await document.GetSemanticModelAsync(token);
            var operation = model?.GetOperation(syntax, token);
            if (operation is ILocalFunctionOperation local) calls.Visit(local.Body);
            else calls.Visit(operation);
        }
        var outgoing = calls.Calls.OrderBy(call => call.Target.ToDisplayString(), StringComparer.Ordinal)
            .ThenBy(call => call.Location.SourceTree?.FilePath, StringComparer.Ordinal)
            .ThenBy(call => call.Location.SourceSpan.Start)
            .Select(call => new { to = Item(call.Target), locations = new[] { Location(call.Location) } }).ToArray();
        return new[] { new { item = Item(symbol), incoming = incoming.ToArray(), outgoing } };
    }

    private sealed class CallWalker(CancellationToken token) : OperationWalker
    {
        public List<(IMethodSymbol Target, Location Location)> Calls { get; } = new();
        public override void Visit(IOperation? operation)
        {
            token.ThrowIfCancellationRequested();
            base.Visit(operation);
        }
        private void Add(IMethodSymbol method, IOperation operation)
        {
            if (Calls.Count >= MaximumEdges) throw new InvalidOperationException("Call hierarchy exceeds 500 outgoing edges");
            Calls.Add((method, operation.Syntax.GetLocation()));
        }
        public override void VisitInvocation(IInvocationOperation operation)
        {
            Add(operation.TargetMethod, operation);
            base.VisitInvocation(operation);
        }
        public override void VisitObjectCreation(IObjectCreationOperation operation)
        {
            if (operation.Constructor is not null) Add(operation.Constructor, operation);
            base.VisitObjectCreation(operation);
        }
        // Nested callable bodies are separate callers; do not attribute their calls
        // to the enclosing method. Dynamic invocations have no statically known target.
        public override void VisitAnonymousFunction(IAnonymousFunctionOperation operation) { }
        public override void VisitLocalFunction(ILocalFunctionOperation operation) { }
    }
}

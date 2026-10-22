# SPDX-License-Identifier: Apache-2.0
"""Test-only guard around Refresh: failed transactions must preserve semantic state."""
def instrument(path):
    source = path.read_text()
    start = source.index('    private async Task Refresh(')
    end = source.index('    // Only documents returned', start)
    method = source[start:end]
    opening = method.index('{') + 1
    closing = method.rfind('}')
    body = method[opening:closing]
    guarded = method[:opening] + '''
        var beforeDocuments = documents.ToArray();
        var beforeFingerprints = fingerprints.ToArray();
        var beforeSnapshots = snapshots.ToArray();
        var beforeSolution = workspace.CurrentSolution;
        try
        {
''' + body + '''
        }
        catch
        {
            if (!beforeDocuments.SequenceEqual(documents) || !beforeFingerprints.SequenceEqual(fingerprints) ||
                !beforeSnapshots.SequenceEqual(snapshots) || !ReferenceEquals(beforeSolution, workspace.CurrentSolution))
            {
                Console.Error.WriteLine("BENCH_TRANSACTION_FAILURE");
                throw new InvalidOperationException("BENCH_TRANSACTION_FAILURE: failed refresh changed committed state");
            }
            Console.Error.WriteLine("BENCH_TRANSACTION_PRESERVED");
            throw;
        }
''' + method[closing:]
    result = source[:start] + guarded + source[end:]
    # A cooperative background transaction permits an independently committed
    # foreground transaction while its private preparation is suspended. Compare
    # failure against that latest legitimate state, not the state before yielding.
    # Foreground Refresh has its own guard. Capture in finally even if the
    # foreground semantic operation throws after successfully refreshing content.
    yield_finally = '                finally { backgroundReading = true; }'
    if yield_finally in result:
        assert result.count(yield_finally) == 1
        result = result.replace(yield_finally, '''                finally
                {
                    backgroundReading = true;
                    beforeDocuments = documents.ToArray();
                    beforeFingerprints = fingerprints.ToArray();
                    beforeSnapshots = snapshots.ToArray();
                    beforeSolution = workspace.CurrentSolution;
                }''')
    anchor = '            // Cached ancestor checks authorize snapshot admission, never a read.'
    assert result.count(anchor) == 1
    result = result.replace(anchor, '            // Generated test-only seam; never part of a production/timed build.\n            if (forceFile == file && File.Exists(Path.Combine(root!, ".swap-before-read")))\n            {\n                File.Delete(Path.Combine(root!, ".swap-before-read"));\n                var directory = Path.GetDirectoryName(file)!;\n                Directory.Move(directory, Path.Combine(root!, ".saved-ancestor"));\n                Directory.CreateSymbolicLink(directory, Path.Combine(Path.GetDirectoryName(root!)!, "outside-ancestor"));\n                Console.Error.WriteLine("BENCH_PRE_READ_SWAP_EXECUTED");\n            }\n' + anchor)
    path.write_text(result)

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
    path.write_text(source[:start] + guarded + source[end:])

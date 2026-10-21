namespace FreeFlight.Roslyn;

// A completed request may still be referenced by an input-loop cancellation or
// EOF snapshot. Lease Cancel calls so completion never disposes their source.
internal sealed class RequestCancellation : IDisposable
{
    private readonly object lifetime = new();
    private readonly CancellationTokenSource source;
    private bool completed;
    private int cancellations;

    public RequestCancellation(TimeSpan timeout)
    {
        source = new CancellationTokenSource(timeout);
        Token = source.Token;
    }

    public CancellationToken Token { get; }

    public void Cancel()
    {
        lock (lifetime)
        {
            if (completed) return;
            cancellations++;
        }
        // Callbacks can run arbitrary continuations, including request completion.
        // Never hold our lifetime lock while invoking them or wait for completion.
        try { source.Cancel(); }
        finally
        {
            lock (lifetime)
                if (--cancellations == 0 && completed) source.Dispose();
        }
    }

    public void Dispose()
    {
        lock (lifetime)
        {
            if (completed) return;
            completed = true;
            if (cancellations == 0) source.Dispose();
        }
    }
}

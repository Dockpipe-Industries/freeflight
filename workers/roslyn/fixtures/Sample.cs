namespace Fixture;
public class Counter
{
    public int Value;
    public int Increment() => ++Value;
}
public class Consumer
{
    public int Read(Counter counter) => counter.Value;
}

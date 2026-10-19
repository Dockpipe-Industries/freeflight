namespace Advanced;
public interface ICalc { int Add(int value, int increment); }
public class Base : ICalc
{
    public virtual int Add(int value, int increment) => value + increment;
}
public class Derived : Base
{
    public override int Add(int value, int increment) => base.Add(value, increment);
}
public class Caller
{
    public int Run() => new Derived().Add(1, 2);
    public int Overload(string value) => value.Length;
    public int Overload(int value) => value;
    public int Invoke() => Overload(42);
    public void Nested() { System.Action later = () => Overload(1); void Local() => Overload(2); }
}

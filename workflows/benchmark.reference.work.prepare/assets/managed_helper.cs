// SPDX-License-Identifier: Apache-2.0
internal static class WorkMeter
{
 [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
 public struct Stamp {public ulong instructions,cycles,cpuNs,beginNs,endNs;public int pid,status;}
 [System.Runtime.InteropServices.DllImport("@LIB@",EntryPoint="ffwork_read")]
 private static extern int Snapshot(out Stamp value);
 [System.Runtime.InteropServices.DllImport("@LIB@",EntryPoint="ffwork_stamp_bytes")]
 private static extern int StampBytes();
 [System.Runtime.InteropServices.DllImport("@LIB@",EntryPoint="ffwork_loop")]
 public static extern ulong Loop(ulong n,ulong seed);
 public static Stamp Read(){if(System.Runtime.InteropServices.Marshal.SizeOf<Stamp>()!=48 || StampBytes()!=48)throw new System.PlatformNotSupportedException("WorkStamp ABI");if(Snapshot(out var s)!=0 || s.status!=0)throw new System.IO.IOException("Work snapshot failed");return s;}
 public static readonly System.Threading.AsyncLocal<object?> Last=new();
}

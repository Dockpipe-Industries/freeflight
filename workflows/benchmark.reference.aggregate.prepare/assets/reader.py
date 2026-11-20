# SPDX-License-Identifier: Apache-2.0
import ctypes,time
class Stamp(ctypes.Structure):
 _fields_=[(x,ctypes.c_uint64) for x in ['instructions','cycles','userMach','systemMach','start','begin','end']]+[(x,ctypes.c_uint32) for x in ['numer','denom']]+[(x,ctypes.c_int32) for x in ['pid','status']]
class Reader:
 def __init__(self,path):
  self.lib=ctypes.CDLL(str(path));self.lib.ff_size.restype=ctypes.c_int;assert self.lib.ff_size()==ctypes.sizeof(Stamp)==72
  self.lib.ff_now.restype=ctypes.c_uint64
  lo=time.clock_gettime_ns(time.CLOCK_MONOTONIC);native=self.lib.ff_now();hi=time.clock_gettime_ns(time.CLOCK_MONOTONIC);assert lo<=native<=hi, 'Native/parent monotonic origins differ'
  self.lib.ff_read.argtypes=[ctypes.c_int,ctypes.POINTER(Stamp)];self.lib.ff_read.restype=ctypes.c_int
 def read(self,pid):
  s=Stamp();status=self.lib.ff_read(pid,ctypes.byref(s));v={k:getattr(s,k) for k,_ in s._fields_};assert status==v['status']==0 and v['start']>0 and v['end']>=v['begin'];return v
 def pair(self,pids):return [self.read(pid) for pid in pids]
def delta(a,b):
 assert all(a[k]==b[k] for k in ['pid','start','numer','denom']) and b['begin']>=a['end']
 d={k:b[k]-a[k] for k in ['instructions','cycles','userMach','systemMach']};assert min(d.values())>=0
 d['cpuNs']=(d['userMach']+d['systemMach'])*a['numer']//a['denom'];return d
def wait(t):
 while True:
  n=t-time.clock_gettime_ns(time.CLOCK_MONOTONIC)
  if n<=0:return
  time.sleep(n/1e9)

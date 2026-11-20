# SPDX-License-Identifier: Apache-2.0
"""Native macOS primitive feasibility, not a Roslyn/MCP performance candidate."""
import concurrent.futures, errno, fcntl, hashlib, json, os, pathlib, platform, re, socket, stat, subprocess, sys, threading

class Cancelled(Exception): pass
class Rejected(Exception): pass


def child(out):
    sdk=pathlib.Path(subprocess.check_output(['xcrun','--show-sdk-path'],text=True).strip())
    header=sdk/'usr/include/sys/fcntl.h'; data=header.read_text()
    match=re.search(r'^#define\s+O_NOFOLLOW_ANY\s+(0x[0-9a-fA-F]+)',data,re.M)
    assert match, 'Unsupported SDK: keep serial runtime'
    anylink=int(match[1],16)
    flags=os.O_RDONLY|os.O_NONBLOCK|os.O_CLOEXEC|anylink
    fixture=out/'fixture';fixture.mkdir();regular=fixture/'source.cs';regular.write_bytes(b'old')
    fifo=fixture/'pipe.cs';os.mkfifo(fifo)
    directory=fixture/'directory.cs';directory.mkdir()
    # AF_UNIX addresses are short; cwd changes only in this disposable child.
    prior=os.getcwd();os.chdir(fixture)
    sock=socket.socket(socket.AF_UNIX);sock.bind('socket.cs');os.chdir(prior)
    link=fixture/'link.cs';link.symlink_to(regular)
    guard=threading.Lock();active=0;peak=0;reads=0;cases=[]
    def check(token):
        if token is not None and token.is_set():raise Cancelled()
    def read(path, token=None, before=None, after=None, fault=False, barrier=None, use_flags=flags, before_read=None):
        nonlocal active,peak,reads
        check(token)
        # Fixture hook models replacement after pathname admission, before open.
        if before:before()
        fd=os.open(path,use_flags)
        with guard:active+=1;peak=max(peak,active)
        try:
            if barrier:barrier.wait(timeout=3)
            if after:after()
            check(token)
            if fault:raise OSError(errno.EIO,'injected fstat failure')
            opened=os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode):raise Rejected('not-regular')
            assert fcntl.fcntl(fd,fcntl.F_GETFD)&fcntl.FD_CLOEXEC
            assert fcntl.fcntl(fd,fcntl.F_GETFL)&os.O_NONBLOCK
            # Diagnostic identity guard, NOT a claim of race-free namespace checks.
            current=os.stat(path,follow_symlinks=False)
            if not stat.S_ISREG(current.st_mode) or (opened.st_dev,opened.st_ino)!=(current.st_dev,current.st_ino):
                raise Rejected('identity-changed')
            check(token)
            if before_read:before_read()
            with guard:reads+=1
            return os.read(fd,8192)
        finally:
            os.close(fd)
            with guard:active-=1
    def case(name,call,expected=None,value=None):
        previous=reads
        try:
            result=call();assert expected is None,(name,'unexpected success')
            assert result==value,(name,result,value)
            detail={'result':result.decode()}
        except (OSError,Rejected,Cancelled) as error:
            assert expected is not None and isinstance(error,expected),(name,repr(error))
            assert reads==previous,(name,'rejected input was read')
            detail={'error':type(error).__name__,'errno':getattr(error,'errno',None),'message':str(error)}
        assert active==0,(name,'descriptor leaked')
        cases.append(dict(name=name,**detail))
    case('regular-bytes-and-flags',lambda:read(regular),value=b'old')
    for name,path in [('fifo',fifo),('directory',directory),('socket',fixture/'socket.cs'),('leaf-symlink',link),('character-device',pathlib.Path('/dev/null'))]:
        case(name,lambda path=path:read(path),expected=(OSError,Rejected))
    outside=out/'outside';outside.mkdir();(outside/'file.cs').write_bytes(b'outside')
    ancestor=fixture/'ancestor';ancestor.symlink_to(outside,target_is_directory=True)
    # Demonstrates leaf-only NOFOLLOW does not defend ancestor components.
    weak=os.open(ancestor/'file.cs',(flags&~anylink)|os.O_NOFOLLOW)
    try:assert os.read(weak,8192)==b'outside'
    finally:os.close(weak)
    cases.append(dict(name='leaf-only-ancestor-negative-control',outsideBytesRead=True,scope='disposable synthetic file'))
    case('all-components-ancestor-symlink',lambda:read(ancestor/'file.cs'),expected=OSError)
    for kind in ['symlink','fifo','directory']:
        replacement=fixture/('replace-'+kind);replacement.write_bytes(b'old')
        def swap(path=replacement,kind=kind):
            path.unlink()
            if kind=='symlink':path.symlink_to(regular)
            elif kind=='fifo':os.mkfifo(path)
            else:path.mkdir()
        case('replacement-before-open-'+kind,lambda p=replacement,s=swap:read(p,before=s),expected=(OSError,Rejected))
    replacement=fixture/'after-open';replacement.write_bytes(b'old')
    def replace():
        replacement.rename(fixture/'saved');replacement.write_bytes(b'new')
    case('replacement-after-open-identity',lambda:read(replacement,after=replace),expected=Rejected)
    deletion=fixture/'delete-after-open';deletion.write_bytes(b'old')
    case('delete-after-open',lambda:read(deletion,after=deletion.unlink),expected=OSError)
    late=fixture/'late-replacement';late.write_bytes(b'old')
    def late_swap():
        late.rename(fixture/'late-saved');late.symlink_to(outside/'file.cs')
    case('identity-check-read-window-negative-control',lambda:read(late,before_read=late_swap),value=b'old')
    assert late.is_symlink()
    changing_parent=fixture/'changing-parent';changing_parent.mkdir();(changing_parent/'file.cs').write_bytes(b'old')
    def parent_swap():
        changing_parent.rename(fixture/'parent-saved');changing_parent.symlink_to(outside,target_is_directory=True)
    case('ancestor-replacement-before-open',lambda:read(changing_parent/'file.cs',before=parent_swap),expected=OSError)
    timestamp=regular.stat().st_mtime_ns
    def edit():
        regular.write_bytes(b'new');os.utime(regular,ns=(timestamp,timestamp))
    case('same-size-restored-time-current-bytes',lambda:read(regular,after=edit),value=b'new')
    cancelled=threading.Event();cancelled.set()
    case('pre-cancel',lambda:read(regular,token=cancelled),expected=Cancelled)
    cancelled.clear()
    case('cancel-after-open',lambda:read(regular,token=cancelled,after=cancelled.set),expected=Cancelled)
    case('fstat-fault-closes-handle',lambda:read(regular,fault=True),expected=OSError)
    for width in [2,4]:
        barrier=threading.Barrier(width);peak=0;before_reads=reads
        def run(i):
            try:read(fifo,barrier=barrier)
            except Rejected as e:return (i,str(e))
            raise AssertionError('FIFO accepted')
        with concurrent.futures.ThreadPoolExecutor(max_workers=width) as pool:
            outcomes=list(pool.map(run,range(width)))
        assert active==0 and peak==width and reads==before_reads
        # Earlier sorted admission error wins regardless of later completion order.
        errors=[(0,'maxFileBytes:A:2:1')]+[(i+1,e) for i,e in outcomes]
        assert min(errors)[1]=='maxFileBytes:A:2:1'
        cases.append(dict(name='bounded-fifo-drain-'+str(width),peakDescriptors=peak,retainedDescriptors=active,bytesRead=0,earliestError=min(errors)[1]))
    for width in [2,4]:
        barrier=threading.Barrier(width);stop=threading.Event();peak=0;before_reads=reads
        def run_cancel(i):
            try:read(regular,token=stop,barrier=barrier,after=stop.set)
            except Cancelled:return i
            raise AssertionError('cancelled operation read bytes')
        with concurrent.futures.ThreadPoolExecutor(max_workers=width) as pool:
            assert list(pool.map(run_cancel,range(width)))==list(range(width))
        assert active==0 and peak==width and reads==before_reads
        cases.append(dict(name='bounded-cancel-drain-'+str(width),peakDescriptors=peak,retainedDescriptors=active,bytesRead=0))
    eventmatch=re.search(r'^#define\s+O_EVTONLY\s+(0x[0-9a-fA-F]+)',data,re.M)
    assert eventmatch
    eventfd=os.open(regular,int(eventmatch[1],16)|os.O_CLOEXEC|anylink)
    try:
        assert stat.S_ISREG(os.fstat(eventfd).st_mode)
        observations=[]
        for change in [False,True]:
            if change:fcntl.fcntl(eventfd,fcntl.F_SETFL,os.O_RDONLY|os.O_NONBLOCK)
            os.lseek(eventfd,0,os.SEEK_SET)
            value=os.read(eventfd,3)
            assert value==b'new'
            observations.append(dict(afterSetfl=change,flags=fcntl.fcntl(eventfd,fcntl.F_GETFL),bytes=value.decode()))
        cases.append(dict(name='event-only-is-readable-on-this-host',observations=observations))
    finally:os.close(eventfd)
    sock.close()
    return dict(status='local-primitive-gates-passed',runtimeCandidateQualified=False,cases=cases,
        sdk=str(sdk),headerSha256=hashlib.sha256(header.read_bytes()).hexdigest(),flags=flags,
        host=platform.platform(),python=sys.version,sourceCommit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        assetSha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        limits=['Native Python os.open/fstat probe, not .NET interop or worker qualification',
        'No bounded cancellation claim for an in-flight kernel syscall',
        'Identity check is not atomic with subsequent read',
        'Character-device case opens only /dev/null and performs no content read',
        'No device nodes, mounts, permissions, runtime settings or remote services changed'])

if len(sys.argv)>1:
    out=pathlib.Path(sys.argv[1]);result=child(out)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
else:
    assert platform.system()=='Darwin'
    label=os.environ.get('FREEFLIGHT_RECOVERY_HANDLES_LABEL','handles-v1')
    assert label and all(c.isalnum() or c in '-_' for c in label)
    out=(pathlib.Path.cwd()/'bin/.local/benchmarks/recovery-handles'/label).resolve();out.mkdir(parents=True,exist_ok=False)
    frozen=out/'probe-source.py';frozen.write_bytes(pathlib.Path(__file__).read_bytes())
    with (out/'probe.log').open('w') as log:
        subprocess.run([sys.executable,str(frozen),str(out)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=30)
    print((out/'result.json').read_text())

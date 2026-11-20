# SPDX-License-Identifier: Apache-2.0
"""Freeze matched native cores; reuse one qualified exact94 worker for both."""
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
repo=Path.cwd();label=os.environ['FREEFLIGHT_RESPONSE_LABEL'];assert label and all(c.isalnum() or c in '-_' for c in label)
out=repo/'bin/.local/benchmarks/response-copies'/label;out.mkdir(parents=True,exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,v):(out/name).write_text(json.dumps(v,indent=2)+'\n')
receipt=repo/'bin/.local/benchmarks/trusted/native-attributes-screen-v1';config=json.loads((receipt/'provenance.json').read_text())
worker=config['variants']['baseline'];assert sha(Path(worker['dll']))==worker['dllSha256']
for name,h in worker['sourceHashes'].items():assert hashlib.sha256(subprocess.check_output(['git','show','94eb420:'+name])).hexdigest()==h,name
cmake='/Users/jamie/Documents/Codex/2026-10-19/task/toolchains/cmake-3.31.8-macos-universal/CMake.app/Contents/bin/cmake';ctest=str(Path(cmake).with_name('ctest'));jsonSource=repo/'bin/.local/build/_deps/json-src'
names=['CMakeLists.txt','README.md','LICENSE']+subprocess.check_output(['git','ls-files','src','include','tests'],text=True).splitlines()
manifest=dict(status='preparing',head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),workerReceipt=str(receipt),workerProvenanceSha256=sha(receipt/'provenance.json'),worker=worker,dotnet=config['dotnet'],workerArgs=config['baselineArgs'],fixtures=config['fixtures'],compilerVersion=subprocess.check_output(['c++','--version'],text=True),cmake=cmake,variants={})
assert manifest['workerArgs']==['--incremental-validation','--background-recovery']
(out/'start-tracked.patch').write_bytes(subprocess.check_output(['git','diff','--binary']))
for asset in Path(__file__).parent.glob('*.py'):shutil.copy2(asset,out/asset.name)
save('manifest.json',manifest)
for variant in ['baseline','candidate']:
 source=out/variant/'source';build=out/variant/'build';source.mkdir(parents=True)
 for name in names:
  target=source/name;target.parent.mkdir(parents=True,exist_ok=True)
  target.write_bytes(subprocess.check_output(['git','show','94eb420:'+name]) if variant=='baseline' else subprocess.check_output(['git','show','94eb420:'+name]))
 from patch import patch_tests,patch_reader
 patch_tests(source/'tests/process.cpp')
 if variant=='candidate':patch_reader(source/'src/process.cpp')
 commands=[[cmake,'-S',str(source),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DFETCHCONTENT_SOURCE_DIR_JSON='+str(jsonSource)],
  [cmake,'--build',str(build),'--parallel','2'],[ctest,'--test-dir',str(build),'--output-on-failure'],
  [sys.executable,'-B',str(repo/'tests/protocol.py'),str(build/'freeflight')]]
 with (out/(variant+'-qualification.log')).open('w') as log:
  for command in commands:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
 manifest['variants'][variant]=dict(binary=str(build/'freeflight'),binarySha256=sha(build/'freeflight'),source=str(source),sourceHashes={name:sha(source/name) for name in names},commands=commands,qualificationSha256=sha(out/(variant+'-qualification.log')))
 save('manifest.json',manifest);print(variant,'core + current dual-content protocol gates passed',flush=True)
manifest['scope']='Generated incremental newline scan + iterator JSON input only; no capability changes/worker/validation changes. Both variants get identical additional framing tests.';manifest['status']='passed';manifest['adapterSha256']=sha(Path(__file__));manifest['protocolTestSha256']=sha(repo/'tests/protocol.py');save('manifest.json',manifest)

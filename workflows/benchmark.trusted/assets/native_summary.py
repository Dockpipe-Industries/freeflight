# SPDX-License-Identifier: Apache-2.0
"""Join generated native traces by protocol IDs; never infer recovery from latency."""
import hashlib,json,statistics
from pathlib import Path
import run as trusted

def summarize(receipt):
    receipt=Path(receipt);sessions=json.loads((receipt/'samples.json').read_text());rows=[];tails=[];joinedCount=0
    for session in sessions:
        assert session['diagnostic']
        maps={'CORE_PROFILE ':{},'BENCH_PROFILE ':{}}
        for line in (receipt/session['name']/'server.stderr.log').read_text().splitlines():
            for prefix,records in maps.items():
                if prefix in line:
                    value=json.loads(line.split(prefix,1)[1]);key=str(value['id']);assert key not in records,(session['name'],prefix,key)
                    records[key]=value
        joined=[]
        for sample in session['samples']:
            core=maps['CORE_PROFILE '][str(sample['requestId'])];assert len(core['workerIds'])==1
            worker=maps['BENCH_PROFILE '][str(core['workerIds'][0])];assert worker['method']==sample['method']
            joined.append({'sample':sample,'core':core,'worker':worker});joinedCount+=1
        for phase in ['steady','idle-5.1s']:
            for method in ['symbols','definition','references','workspaceSymbols']:
                selected=[r for r in joined if r['sample']['phase']==phase and r['sample']['method']==method]
                assert selected
                metrics={}
                for group,key in [('core','stages'),('core','threadCpuStages'),('worker','stages'),('sample','clientProfile')]:
                    names=set().union(*(r[group][key].keys() for r in selected))
                    for name in names:
                        values=[r[group][key][name] for r in selected if name in r[group][key] and isinstance(r[group][key][name],(int,float))]
                        if values:metrics[f'{group}.{key}.{name}']=trusted.stats(values)
                for group,names in [('worker',['Reads','Bytes','Expired','Dirty','Invalidated','Reused','Attrs','allocatedBytes','gcPauseMs','gen0','gen1','gen2','poolPending','cpuMs','invokeMs','replyMs','previousProfilePostludeMs']),('core',['processCpuMs','voluntarySwitches','involuntarySwitches'])]:
                    for name in names:metrics[group+'.'+name]=trusted.stats([r[group][name] for r in selected])
                recovery=[r for r in selected if r['worker']['Reads']==session['size']]
                rows.append({'session':session['name'],'variant':session['variant'],'method':method,'phase':phase,'metrics':metrics,
                    'fullRecoveries':len(recovery),'recoveryRequestIds':[r['sample']['requestId'] for r in recovery],
                    'runtimeEventTotals':{k:sum(r['worker']['runtimeEvents'].get(k,0) for r in selected) for k in set().union(*(r['worker']['runtimeEvents'].keys() for r in selected))}})
                tails.extend({'session':session['name'],**r} for r in sorted(selected,key=lambda r:r['sample']['ms'],reverse=True)[:5])
        for method in ['symbols','definition','references','workspaceSymbols']:
            for ordinal in range(4):
                selected=[r for r in joined if r['sample']['phase']=='steady' and r['sample']['method']==method and r['sample']['ordinal']==ordinal]
                if selected:rows.append({'session':session['name'],'variant':session['variant'],'method':method,'phase':'steady-order','ordinal':ordinal,
                    'latency':trusted.stats([r['sample']['ms'] for r in selected]),'workerInvoke':trusted.stats([r['worker']['invokeMs'] for r in selected]),
                    'workerQueue':trusted.stats([r['worker']['stages']['workerQueue'] for r in selected]),'clientParse':trusted.stats([r['sample']['clientProfile']['parseMs'] for r in selected])})
    (receipt/'native-profile-summary.json').write_text(json.dumps({'status':'passed','postprocessorSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'joinedSamples':joinedCount,'rows':rows},indent=2))
    (receipt/'native-profile-tails.json').write_text(json.dumps(tails,indent=2))
    return joinedCount

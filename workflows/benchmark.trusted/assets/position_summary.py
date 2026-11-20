# SPDX-License-Identifier: Apache-2.0
"""Retain conditional latency and actual response-to-request gaps, without filtering."""
import hashlib
import json
import os
from pathlib import Path
import run as trusted

def summarize(root, overrides=None):
    root=Path(root);rows=[];completed=[];interrupted=[]
    overrides=overrides or {}
    assert set(overrides)<={'aa-equal-gap'}
    for mode in ['before-native','fixed-native','fixed-diagnostic-qualification']:
        receipt=root.with_name(root.name+'-'+mode)
        qualification=json.loads((receipt/'qualification-only.json').read_text())
        assert qualification['status']=='passed' and qualification['timedProcesses']==0
        completed.append({'mode':mode,'receipt':str(receipt),'prepareOnly':True})
    for mode in ['lifetime-balanced','aa-fixed','aa-balanced','aa-equal-gap']:
        original=root.with_name(root.name+'-'+mode)
        receipt=Path(overrides.get(mode,original))
        assert json.loads((receipt/'summary.json').read_text())['status']=='passed'
        provenance=json.loads((receipt/'provenance.json').read_text())
        assert not provenance.get('cadenceCrossover',False)
        expectedOrder='fixed' if mode=='aa-fixed' else 'balanced'
        expectedGap=.02 if mode=='aa-equal-gap' else 0
        expectedIntervals=[0,.1] if mode=='lifetime-balanced' else [0] if mode=='aa-equal-gap' else [.1]
        expectedSizes={'433','5845'} if mode=='lifetime-balanced' else {'5845'}
        assert provenance['queryOrder']==expectedOrder and provenance['queryGapSeconds']==expectedGap
        assert provenance['intervals']==expectedIntervals and set(provenance['fixtures'])==expectedSizes
        if mode.startswith('aa-'):assert provenance['identicalBinaryControl'] and provenance['sharedWorker']
        sessions=json.loads((receipt/'samples.json').read_text())
        assert len(sessions)==provenance['sessions']*2*len(expectedIntervals)*len(expectedSizes)
        assert all(s['status']=='passed' and not s['diagnostic'] for s in sessions)
        for size in expectedSizes:
            for interval in expectedIntervals:
                for variant in ['local-baseline','candidate']:
                    assert sum(s['size']==int(size) and s['interval']==interval and s['variant']==variant for s in sessions)==provenance['sessions']
        if receipt!=original:
            assert not (original/'summary.json').exists(), 'Do not replace a completed condition'
            originalProvenance=json.loads((original/'provenance.json').read_text())
            for key in ['rounds','sessions','warmupSeconds','sdk','sdkRoot','queryOrder','queryGapSeconds','intervals','fixtures','requestedProducts']:
                assert provenance[key]==originalProvenance[key], 'Recovery condition drift: '+key
            for key in ['candidate','localBaseline','candidateCore','local-baselineCore']:
                assert provenance[key]['sourceHashes']==originalProvenance[key]['sourceHashes'], 'Recovery source drift: '+key
            partial=json.loads((original/'samples.json').read_text())
            assert len(partial)<len(sessions), 'Recover complete saved sessions instead of replacing them'
            interrupted.append({'mode':mode,'receipt':str(original),'replacement':str(receipt),
                                'completedProcesses':sum(s['status']=='passed' for s in partial),
                                'note':'Original executor run was interrupted. All original samples and partial process directories remain; replacement is a fresh complete condition, not selected samples.'})
        completed.append({'mode':mode,'receipt':str(receipt),'prepareOnly':False,'processes':len(sessions)})
        for session in sessions:
            selected=[s for s in session['samples'] if s['phase']=='steady']
            assert len(selected)==provenance['rounds']*4
            assert sum(s['phase']=='idle-5.1s' for s in session['samples'])==4
            if session['queryOrder']=='balanced':
                # Validate each complete design block from actual recorded samples.
                for block in range(len(selected)//16):
                    samples=selected[block*16:(block+1)*16]
                    assert len({(s['method'],s['ordinal']) for s in samples})==16
                    edges={(s['previousMethod'],s['method']) for s in samples if s['ordinal']>0}
                    assert len(edges)==12 and all(a!=b for a,b in edges)
            for method in ['symbols','definition','references','workspaceSymbols']:
                for ordinal in range(4):
                    for previous in sorted({s['previousMethod'] for s in selected if s['method']==method and s['ordinal']==ordinal}):
                        samples=[s for s in selected if (s['method'],s['ordinal'],s['previousMethod'])==(method,ordinal,previous)]
                        rows.append({'mode':mode,'session':session['name'],'variant':session['variant'],
                                     'size':session['size'],'interval':session['interval'],'method':method,
                                     'ordinal':ordinal,'previousMethod':previous,
                                     'latency':trusted.stats([s['ms'] for s in samples]),
                                     'actualGap':trusted.stats([s['gapBeforeMs'] for s in samples])})
    (root/'position-summary.json').write_text(json.dumps({'status':'passed','rows':rows,
        'postprocessorSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'limits':'Gap includes Python oracle/receipt processing and deliberate sleep. Position and spacing are manipulated; no CPU frequency/cache/scheduler mechanism is inferred. No tail or recovery sample removed.'},indent=2))
    (root/'completion-review.json').write_text(json.dumps({'status':'passed','conditions':completed,
        'interruptedConditions':interrupted,'note':'Validates complete condition receipts; does not relabel an interrupted orchestrator as successful.'},indent=2))


def summarize_crossover(receipt):
    receipt=Path(receipt)
    assert json.loads((receipt/'summary.json').read_text())['status']=='passed'
    provenance=json.loads((receipt/'provenance.json').read_text())
    assert provenance['cadenceCrossover'] and provenance['identicalBinaryControl'] and provenance['sharedWorker']
    assert provenance['queryOrder']=='balanced' and provenance['rounds']%8==0
    assert provenance['intervals']==[.1] and provenance['queryGapSeconds']==.02
    sessions=json.loads((receipt/'samples.json').read_text());rows=[]
    assert len(sessions)==provenance['sessions']*2
    for session in sessions:
        assert session['status']=='passed' and not session['diagnostic'] and session['size']==5845
        selected=[s for s in session['samples'] if s['phase']=='steady']
        assert len(selected)==provenance['rounds']*4
        for start in range(0,len(selected),16):
            block=selected[start:start+16]
            assert len({s['cadence'] for s in block})==1
            assert len({(s['method'],s['ordinal']) for s in block})==16
            assert len({(s['previousMethod'],s['method']) for s in block if s['ordinal']>0})==12
        for method in ['symbols','definition','references','workspaceSymbols']:
            for ordinal in range(4):
                policies={}
                for cadence in ['round','query-delay']:
                    samples=[s for s in selected if (s['method'],s['ordinal'],s['cadence'])==(method,ordinal,cadence)]
                    assert len(samples)==provenance['rounds']//8
                    policies[cadence]={'latency':trusted.stats([s['ms'] for s in samples]),
                                       'actualGap':trusted.stats([s['gapBeforeMs'] for s in samples])}
                rows.append({'session':session['name'],'method':method,'ordinal':ordinal,'policies':policies,
                             'blockBoundaryCarryover':any(s['method']==method and s['ordinal']==ordinal and s['round']%4==0 and ordinal==0 for s in selected),
                             'medianDelayToRoundRatio':policies['query-delay']['latency']['median']/policies['round']['latency']['median']})
    (receipt/'crossover-summary.json').write_text(json.dumps({'status':'passed','rows':rows,
        'postprocessorSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'limits':'Policies alternate every four balanced rounds within each process; starting policy alternates across processes. All samples retained. Identifies cadence-context effects, not a hardware/runtime mechanism; position and predecessor remain coupled within this design.'},indent=2))


def complete_review(root,crossover):
    root=Path(root);crossover=Path(crossover)
    primary=json.loads((root/'completion-review.json').read_text())
    assert primary['status']==json.loads((crossover/'crossover-summary.json').read_text())['status']=='passed'
    receipts=[Path(c['receipt']) for c in primary['conditions'] if not c['prepareOnly']]+[crossover]
    sessions=[s for receipt in receipts for s in json.loads((receipt/'samples.json').read_text())]
    (root/'final-review.json').write_text(json.dumps({'status':'passed',
        'fixedRef':json.loads((root/'provenance.json').read_text())['fixedRef'],
        'completeProcesses':len(sessions),'steadyChecks':sum(sum(x['phase']=='steady' for x in s['samples']) for s in sessions),
        'idleChecks':sum(sum(x['phase']=='idle-5.1s' for x in s['samples']) for s in sessions),
        'primaryReview':str(root/'completion-review.json'),'crossoverReview':str(crossover/'crossover-summary.json'),
        'interruptedConditions':primary['interruptedConditions'],
        'scope':'Local semantic/correctness qualification and ordinary controls; not acceptance of every performance cell or remote-platform qualification.'},indent=2))


if __name__=='__main__':
    root=trusted.REPO/'bin/.local/glider-comparison'/os.environ['FREEFLIGHT_POSITION_LABEL']
    replacement=os.environ.get('FREEFLIGHT_POSITION_EQUAL_GAP_RECEIPT')
    summarize(root,{'aa-equal-gap':replacement} if replacement else None)
    crossover=os.environ.get('FREEFLIGHT_POSITION_CROSSOVER_RECEIPT')
    if crossover:
        summarize_crossover(crossover)
        complete_review(root,crossover)

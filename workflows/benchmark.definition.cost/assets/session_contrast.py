# SPDX-License-Identifier: Apache-2.0
"""Describe prior matched session cycles without replacing its aggregate result."""
import hashlib,json,statistics
from pathlib import Path

def contrast(receipt):
 raw=receipt/'samples.json';records=json.loads(raw.read_text());rows=[]
 assert len(records)==9
 for method in ['definition','references','workspaceSymbols']:
  ratios=[];cycles=[]
  for cycle in range(3):
   group=records[cycle*3:cycle*3+3]
   assert {r['variant'] for r in group}=={'local-baseline','candidate','glider'}
   medians={r['variant']:statistics.median(x['ms'] for x in r['samples'] if x['phase']=='steady' and x['method']==method) for r in group}
   ratio=medians['candidate']/medians['local-baseline'];ratios.append(ratio)
   cycles.append(dict(cycle=cycle,sessions=[r['name'] for r in group],mediansMs=medians,candidateBaselineMedianRatio=ratio))
  rows.append(dict(method=method,cycles=cycles,medianOfCycleRatios=statistics.median(ratios)))
 return dict(source=str(raw),sourceSha256=hashlib.sha256(raw.read_bytes()).hexdigest(),scope='Descriptive session-cycle contrast; distinct estimand from ratio of medians of session medians. Three cycles cannot establish significance, equivalence, causation or an acceptance threshold. Original aggregate and every adverse cell remain.',rows=rows)

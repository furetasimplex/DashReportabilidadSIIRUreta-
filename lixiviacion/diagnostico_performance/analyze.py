"""Análisis local de planes XML y mediciones; sin conexión SQL."""
from collections import Counter
import json
from pathlib import Path
import statistics
import xml.etree.ElementTree as ET

OUT=Path(__file__).parent
NS={'s':'http://schemas.microsoft.com/sqlserver/2004/07/showplan'}


def owned(node,tag):
    results=[]
    for child in node:
        if child.tag.endswith('}RelOp'): continue
        if child.tag.endswith('}'+tag): results.append(dict(child.attrib))
        results.extend(owned(child,tag))
    return results


def plan(path):
    root=ET.parse(path).getroot()
    report={'file':path.name,'statements':[]}
    for stmt in root.findall('.//s:StmtSimple',NS):
        item={'attributes':dict(stmt.attrib),'operators':[]}
        qp=stmt.find('s:QueryPlan',NS)
        if qp is None: continue
        item['query_plan']=dict(qp.attrib)
        for name in ('MemoryGrantInfo','QueryTimeStats','WaitStats','Warnings','MissingIndexes','ParameterList'):
            item[name]=[ET.tostring(x,encoding='unicode') for x in qp.findall('.//s:'+name,NS)]
        for node in qp.findall('.//s:RelOp',NS):
            r=dict(node.attrib)
            counters=[dict(x.attrib) for x in node.findall('s:RunTimeInformation/s:RunTimeCountersPerThread',NS)]
            r['threads']=counters
            for name in ('ActualRows','ActualRowsRead','ActualExecutions','ActualLogicalReads','ActualPhysicalReads','ActualReadAheads','ActualCPUms'):
                r[name]=sum(float(t.get(name,0)) for t in counters)
            r['ActualElapsedms']=max([float(t.get('ActualElapsedms',0)) for t in counters] or [0])
            r['objects']=owned(node,'Object')
            r['predicates']=owned(node,'ScalarOperator')[:30]
            executions=r['ActualExecutions']
            estimate=float(r.get('EstimateRows',0))
            r['actual_rows_per_execution']=r['ActualRows']/executions if executions else None
            r['ratio_per_execution']=r['actual_rows_per_execution']/estimate if executions and estimate else None
            item['operators'].append(r)
        item['operator_counts']=dict(Counter(r['PhysicalOp'] for r in item['operators']))
        item['conversions']=[dict(x.attrib) for x in qp.findall('.//s:Convert',NS) if x.get('Implicit')=='1']
        report['statements'].append(item)
    return report


def main():
    measurements=json.loads((OUT/'mediciones.json').read_text(encoding='utf-8'))
    groups={}
    for m in measurements:
        if m['with_statistics_xml']: continue
        groups.setdefault(m['label'],[]).append(m)
    summary=[]
    for label,ms in groups.items():
        times=[m['client_seconds'] for m in ms]
        summary.append({'label':label,'min':min(times),'median':statistics.median(times),'max':max(times),
                        'observed_seconds':times,'rows':[m['rows'] for m in ms],
                        'execution_cpu_ms':[m['time_messages'][-1]['cpu_ms'] if m['time_messages'] else None for m in ms],
                        'execution_elapsed_ms':[m['time_messages'][-1]['elapsed_ms'] if m['time_messages'] else None for m in ms],
                        'logical_reads':[sum(x['logical_reads'] for x in m['io']) for m in ms]})
    (OUT/'resumen.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    reports=[plan(p) for p in (OUT/'plans').glob('*.sqlplan')]
    (OUT/'planes_analizados.json').write_text(json.dumps(reports,indent=2)+'\n',encoding='utf-8')
    for r in reports:
        for s in r['statements']:
            print(r['file'],s['query_plan'],s['operator_counts'])
            print('TIME',s['QueryTimeStats'],'WAITS',s['WaitStats'])


if __name__=='__main__': main()

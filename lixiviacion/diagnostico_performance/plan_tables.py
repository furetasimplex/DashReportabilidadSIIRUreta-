"""Extractos verificables del XML real; procesamiento local, sin SQL."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from .analyze import NS, owned

P=Path(__file__).parent


def run():
    lines=['# Operadores de los planes reales', '', 'Tiempos inclusivos: no sumar padres e hijos. Estimación y real/ejecución se comparan por ejecución, no contra el total acumulado.', '']
    for path in sorted((P/'plans').glob('*.sqlplan')):
        if 'probe' in path.name: continue
        root=ET.parse(path).getroot()
        lines+=['## '+path.name, '']
        for stmt in root.findall('.//s:StmtSimple',NS):
            qp=stmt.find('s:QueryPlan',NS)
            if qp is None: continue
            lines+=['```json',json.dumps(dict(stmt.attrib),ensure_ascii=False,indent=2),'```','',
                    '| Nodo | Padre | Operador | Est filas | Real total | Ejecuciones | Real/ejec | IO lógico | CPU ms | Elapsed ms | Objeto |',
                    '|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|']
            def walk(node,parent='—'):
                if node.tag.endswith('}RelOp'):
                    counters=node.findall('s:RunTimeInformation/s:RunTimeCountersPerThread',NS)
                    def total(k): return sum(float(x.get(k,0)) for x in counters)
                    rows,execs=total('ActualRows'),total('ActualExecutions')
                    elapsed=max([float(x.get('ActualElapsedms',0)) for x in counters] or [0])
                    objects=', '.join(x.get('Table','')+' '+x.get('Index','') for x in owned(node,'Object'))
                    lines.append(f"| {node.get('NodeId')} | {parent} | {node.get('PhysicalOp')} / {node.get('LogicalOp')} | {node.get('EstimateRows')} | {rows:g} | {execs:g} | {rows/execs if execs else 0:.3f} | {total('ActualLogicalReads'):g} | {total('ActualCPUms'):g} | {elapsed:g} | {objects} |")
                    parent=node.get('NodeId')
                for child in node: walk(child,parent)
            walk(qp)
    (P/'operadores_planes.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__=='__main__': run()

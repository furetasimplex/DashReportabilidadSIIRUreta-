"""Produce human review artifacts from captured before/after evidence."""
import difflib
import json
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
before = json.loads((HERE / "live_before.json").read_text(encoding="utf-8"))
deploy = json.loads((HERE / "post_deploy_validation.json").read_text(encoding="utf-8"))
post = json.loads((HERE / "post_commit_readonly.json").read_text(encoding="utf-8"))
sim = json.loads((HERE / "simulation_20260901_15.json").read_text(encoding="utf-8"))
idempotence = json.loads((HERE / "idempotencia.json").read_text(encoding="utf-8"))

def key(rows, cols):
    return {tuple(str(r[c]) for c in cols):r for r in rows}

baseline = key(deploy["before"]["cv25"], ("fecha",))
current = key(post["results"]["cv25"], ("fecha",))
normal = [d for d in baseline if d[0] <= "2026-09-05" or d[0] >= "2026-09-12"]
normal_diffs = []
for d in normal:
    for col in current[d]:
        if col in baseline[d] and baseline[d][col] != current[d][col]:
            normal_diffs.append((d[0],col,baseline[d][col],current[d][col]))

graph_before = key(deploy["before"]["graph"], ("fecha",))
graph_after = key(post["results"]["graph"], ("fecha",))
topo_equal = all(graph_before[d]["tms_topografia"] == graph_after[d]["tms_topografia"] for d in graph_before)

old_performance = key([r for r in before["results"]["rendimiento"] if "2026-09-01" <= str(r["fecha"]) <= "2026-09-15"], ("fecha","rotopala_id"))
new_performance = key(post["results"]["rendimiento"], ("fecha","rotopala_id"))
performance_diff = []
for k in sorted(old_performance.keys() | new_performance.keys()):
    a,b = old_performance.get(k,{}),new_performance.get(k,{})
    for c in sorted(set(a)|set(b)):
        if a.get(c)!=b.get(c):
            performance_diff.append({"key":k,"column":c,"before":a.get(c),"after":b.get(c)})

reg = {"normal_days":len(normal),"normal_differences":normal_diffs,
       "topografia_unchanged":topo_equal,
       "hours_unchanged":deploy["before"]["hours"]==post["results"]["hours"],
       "other_equipment_unchanged":deploy["before"]["other_equipment"]==post["results"]["other_equipment"],
       "preliminar_rows_september_before":len([r for r in before["results"]["preliminar"] if "2026-09-01"<=str(r["fecha_operacion"])<="2026-09-15"]),
       "preliminar_rows_september_after":len(post["results"]["preliminar"]),
       "preliminar_acumulado_rows_september_before":len([r for r in before["results"]["preliminar_acumulado"] if "2026-09-01"<=str(r["fecha_operacion"])<="2026-09-15"]),
       "preliminar_acumulado_rows_september_after":len(post["results"]["preliminar_acumulado"]),
       "rendimiento_differences":performance_diff,
       "missing_tum_case":post["results"]["missing_tum"],
       "idempotence":idempotence,
       "before_hashes":{x["name"]:x["sha256"] for x in before["objects"]},
       "after_hashes":{x["name"]:x["sha256"] for x in post["results"]["modified_objects"]},
       "constraint_before":before["constraints_cv25_diario"],
       "constraint_after":post["results"]["cv25_constraints"]}
(HERE / "regression_normal_days.json").write_text(json.dumps(reg,ensure_ascii=False,default=str,indent=2),encoding="utf-8")

expected = {"2026-09-07":"31387","2026-09-08":"4616","2026-09-09":"0",
            "2026-09-10":"41234","2026-09-11":"63252"}
assert not normal_diffs and topo_equal and reg["hours_unchanged"] and reg["other_equipment_unchanged"]
assert all(Decimal(str(current[(d,)]["tms_dia"]))==Decimal(v) for d,v in expected.items())

lines = ["# Episodio CV025 detectado automáticamente: 07–11 septiembre 2026", "",
         "Inicio: 07-B con PI técnicamente plano y TUM_DIRECTO positivo. Recuperación: 11-A.",
         "La conciliación usa PI **diario** de `vista_resumen_datos_filtrados`, que es el contrato de `cv25_diario`; la suma PI por turnos no reproduce exactamente ese contrato el 11.",
         "", "| Fecha | PI crudo | TUM completo | Resuelto | Estado |", "|---|---:|---:|---:|---|"]
for r in sim:
    if "2026-09-06"<=r["fecha"]<="2026-09-11":
        lines.append(f"| {r['fecha']} | {r['PI_diario']} | {r['TUM_diario']} | {r['valor_resuelto_propuesto']} | {r['estado_episodio']} |")
lines += ["", "Masa 07–11: PI crudo **140.489 TMS** = TUM/resuelto **140.489 TMS**; residual **0**. El 06 permanece en cero. No se usaron Topografía, MINA ni IMP para calcular CV025."]
(HERE / "episodio_0709_1109.md").write_text("\n".join(lines)+"\n",encoding="utf-8")

old_defs = {x["name"]:(x["definition"] or "").replace("\r\r\n","\n").splitlines(keepends=True) for x in before["objects"]}
ddl = (HERE/"ddl_deploy.sql").read_text(encoding="utf-8")
parts = [x.strip() for x in __import__("re").split(r"(?im)^\s*GO\s*$",ddl) if x.strip()]
patches=[]
for name,index in (("sp_cargar_cv25_horas",2),("v_cv25_diario",3),("v_diferencia_cv25",4)):
    patches.extend(difflib.unified_diff(old_defs[name],parts[index].splitlines(keepends=True),
                                      fromfile=f"LIVE BEFORE {name}",tofile=f"DEV AFTER {name}"))
(HERE/"diff.patch").write_text("".join(patches),encoding="utf-8")
print("normal diffs",len(normal_diffs),"performance diffs",len(performance_diff),
      "topography",topo_equal,"hours",reg["hours_unchanged"],"other equipment",reg["other_equipment_unchanged"])

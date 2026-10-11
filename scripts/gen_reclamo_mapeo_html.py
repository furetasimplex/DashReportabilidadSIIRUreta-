"""Genera auditoria_reclamo/mapeo_reclamo_diario.html desde el canvas de mapeo."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANVAS = (
    Path.home()
    / ".cursor"
    / "projects"
    / "c-Users-crisn-OneDrive-Escritorio-codigo-SIMPLEX-DashReportabilidadSIIR"
    / "canvases"
    / "reclamo-diario-mapeo.canvas.tsx"
)
OUT = ROOT / "auditoria_reclamo" / "mapeo_reclamo_diario.html"


def extraer_objetos(src: str) -> list[dict]:
    bloque = src.split("const OBJETOS: Obj[] = [", 1)[1].split("];", 1)[0]
    objs = []
    for m in re.finditer(r"\{([^}]+)\}", bloque, re.S):
        body = m.group(1)
        def campo(nombre: str) -> str:
            mm = re.search(rf'{nombre}:\s*"([^"]*)"', body)
            return mm.group(1) if mm else ""
        usa_m = re.search(r"usa:\s*\[([^\]]*)\]", body)
        usa_raw = usa_m.group(1) if usa_m else ""
        usa = re.findall(r'"([^"]+)"', usa_raw)
        objs.append(
            {
                "id": campo("id"),
                "esquema": campo("esquema"),
                "nombre": campo("nombre"),
                "tipo": campo("tipo"),
                "capa": campo("capa"),
                "rol": campo("rol"),
                "usa": usa,
            }
        )
    return [o for o in objs if o["id"]]


HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reclamo diario — mapeo de objetos</title>
<style>
  :root {
    --bg: #f4f1ea;
    --ink: #1c1916;
    --muted: #6b645c;
    --line: #d9d2c5;
    --card: #fffcf7;
    --accent: #1f4e79;
    --ok: #2f6f4e;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font: 14px/1.45 "Segoe UI", system-ui, sans-serif;
    color: var(--ink);
    background: var(--bg);
  }
  header, main { max-width: 1280px; margin: 0 auto; padding: 24px 20px; }
  h1 { font-size: 22px; margin: 0 0 6px; }
  h2 { font-size: 16px; margin: 28px 0 10px; }
  p.sub { color: var(--muted); margin: 0 0 18px; }
  .stats { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 18px; }
  .stat { background: var(--card); border: 1px solid var(--line); padding: 10px 14px; min-width: 120px; }
  .stat b { display: block; font-size: 20px; }
  .stat span { color: var(--muted); font-size: 12px; }
  .flow {
    display: flex; flex-direction: column; gap: 8px;
    background: var(--card); border: 1px solid var(--line); padding: 14px;
    font-family: ui-monospace, Consolas, monospace; font-size: 12px; overflow-x: auto;
  }
  .filters { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin: 12px 0; }
  input, select {
    border: 1px solid var(--line); background: var(--card); color: var(--ink);
    padding: 7px 10px; font: inherit;
  }
  input[type=search] { min-width: 260px; }
  label.chk { display: flex; align-items: center; gap: 6px; color: var(--muted); }
  table { width: 100%; border-collapse: collapse; background: var(--card); }
  th, td { border-bottom: 1px solid var(--line); padding: 7px 8px; text-align: left; vertical-align: top; }
  th { font-size: 12px; color: var(--muted); font-weight: 600; position: sticky; top: 0; background: var(--card); }
  tr.sel td { outline: 1px solid var(--accent); }
  tr.done td { color: var(--ok); }
  button.link {
    background: none; border: 0; color: var(--accent); cursor: pointer;
    font: inherit; text-align: left; padding: 0;
  }
  .detail { margin-top: 16px; background: var(--card); border: 1px solid var(--line); padding: 14px 16px; }
  .pills { display: flex; gap: 8px; flex-wrap: wrap; }
  .pill { border: 1px solid var(--line); padding: 2px 8px; font-size: 12px; }
  .pill.on { background: var(--accent); color: #fff; border-color: var(--accent); }
  code { font-family: ui-monospace, Consolas, monospace; font-size: 12px; }
  footer { color: var(--muted); font-size: 12px; margin-top: 24px; }
  @media print {
    .filters, input[type=checkbox] { }
    header { padding-bottom: 0; }
  }
</style>
</head>
<body>
<header>
  <h1>Reclamo diario — mapeo de objetos</h1>
  <p class="sub">PROD inventar_SpcHidr_PROD · 2026-10-07. Centro:
    <code>reclamo.v_reclamo_diario</code> →
    <code>sp_calcular_reclamo_diario</code> →
    <code>calculo_diario</code>.
    La columna Ref es solo una marca local de seguimiento (se guarda en este navegador).</p>
  <div class="stats">
    <div class="stat"><b id="n-total">0</b><span>Objetos</span></div>
    <div class="stat"><b id="n-filtro">0</b><span>Tras filtros</span></div>
    <div class="stat"><b id="n-ref">0</b><span>Marcados en checklist</span></div>
  </div>
  <h2>Cadena general</h2>
  <div class="flow">
    inventar_SpcHidr.control_reclamo_diario / control_reclamo_sulfuro_* / control_medicion_topografia_diaria<br>
    inventar_SpcHidr.disponible_rotopalas / modulo / datos_filtrados → vista_resumen_datos_filtrados<br>
    ↓  sp_sincronizar_desde_etl  ·  sp_cargar_cv25_horas  ·  sp_congelar_modulo<br>
    reclamo.topografia_avance / camiones_reclamo / cv25_diario / rotopala_horas_turno / modulo_congelado<br>
    ↓<br>
    v_modulo_base · v_topografia_resuelta · v_camiones_acumulado · v_cv25_diario · v_ajustes_aplicables<br>
    ↓  v_preliminar_cv25 → v_preliminar_cv25_con_acumulado<br>
    <b>v_reclamo_diario</b><br>
    ↓  sp_calcular_reclamo_diario → calculo_diario (avance del panel)<br>
    v_cuadratura_modulo · v_diferencia_cv25 · v_rendimiento_rotopala · v_reclamo_para_conciliados → Publicar
  </div>
</header>
<main>
  <h2>Inventario</h2>
  <div class="filters">
    <input id="q" type="search" placeholder="Buscar nombre, rol o dependencia…">
    <select id="esquema">
      <option value="todos">Ambos esquemas</option>
      <option value="reclamo">reclamo</option>
      <option value="inventar_SpcHidr">inventar_SpcHidr</option>
    </select>
    <select id="tipo">
      <option value="Todos">Todos los tipos</option>
      <option>Tabla</option><option>Vista</option><option>SP</option><option>Función</option>
    </select>
    <select id="capa">
      <option value="Todas">Todas las capas</option>
      <option>Fuente</option><option>Persistencia</option><option>Cálculo</option>
      <option>Materialización</option><option>Dashboard</option><option>Publicación</option>
      <option>Contingencia</option>
    </select>
    <label class="chk"><input type="checkbox" id="pend"> Solo pendientes</label>
  </div>
  <table>
    <thead>
      <tr>
        <th>Ref</th><th>Objeto</th><th>Tipo</th><th>Capa</th><th>Rol</th><th>Usa</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
  <div class="detail" id="detail" hidden></div>
  <footer>Checklist local (localStorage). No modifica la base. Definiciones SQL en sql_definitions/.</footer>
</main>
<script>
const OBJETOS = __DATA__;
const KEY = "reclamo-diario-ref-checklist";
const BY = Object.fromEntries(OBJETOS.map(o => [o.id, o]));
const USADO = {};
for (const o of OBJETOS) for (const d of o.usa) (USADO[d] ||= []).push(o.id);
function loadRef(){ try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch { return {}; } }
function saveRef(r){ localStorage.setItem(KEY, JSON.stringify(r)); }
let ref = loadRef();
let sel = "rec.v_reclamo_diario";
function label(id){ return BY[id] ? BY[id].nombre : id; }
function full(o){ return o.esquema + "." + o.nombre; }
function filtrar(){
  const q = document.getElementById("q").value.trim().toLowerCase();
  const esq = document.getElementById("esquema").value;
  const tipo = document.getElementById("tipo").value;
  const capa = document.getElementById("capa").value;
  const pend = document.getElementById("pend").checked;
  return OBJETOS.filter(o => {
    if (esq !== "todos" && o.esquema !== esq) return false;
    if (tipo !== "Todos" && o.tipo !== tipo) return false;
    if (capa !== "Todas" && o.capa !== capa) return false;
    if (pend && ref[o.id]) return false;
    if (!q) return true;
    return (o.nombre + " " + o.rol + " " + o.esquema + " " + o.usa.map(label).join(" ")).toLowerCase().includes(q);
  });
}
function render(){
  const rows = filtrar();
  document.getElementById("n-total").textContent = OBJETOS.length;
  document.getElementById("n-filtro").textContent = rows.length;
  document.getElementById("n-ref").textContent = OBJETOS.filter(o => ref[o.id]).length + "/" + OBJETOS.length;
  document.getElementById("tbody").innerHTML = rows.map(o => {
    const deps = o.usa.length ? o.usa.map(label).join(", ") : "—";
    const cls = [o.id===sel ? "sel" : "", ref[o.id] ? "done" : ""].join(" ").trim();
    return `<tr class="${cls}" data-id="${o.id}">
      <td><input type="checkbox" class="ref" ${ref[o.id]?"checked":""}></td>
      <td><button class="link pick">${full(o)}</button></td>
      <td>${o.tipo}</td><td>${o.capa}</td><td>${o.rol}</td><td><code>${deps}</code></td>
    </tr>`;
  }).join("");
  const o = BY[sel];
  const box = document.getElementById("detail");
  if (!o) { box.hidden = true; return; }
  const deps = o.usa.map(id => BY[id]).filter(Boolean);
  const used = (USADO[o.id]||[]).map(id => BY[id]).filter(Boolean);
  box.hidden = false;
  box.innerHTML = `<h2>${full(o)}</h2>
    <p>${o.rol}</p>
    <div class="pills"><span class="pill on">${o.capa}</span><span class="pill">${o.tipo}</span></div>
    <p><b>Depende de (${deps.length})</b><br>${deps.length ? deps.map(d => `<code>${full(d)}</code>`).join("<br>") : "Tabla fuente / destino escrito."}</p>
    <p><b>Lo usan (${used.length})</b><br>${used.length ? used.map(d => `<code>${full(d)}</code> · ${d.tipo}`).join("<br>") : "Nadie más en este mapa."}</p>`;
}
document.getElementById("tbody").addEventListener("click", e => {
  const tr = e.target.closest("tr");
  if (!tr) return;
  if (e.target.classList.contains("ref")) {
    ref[tr.dataset.id] = e.target.checked;
    saveRef(ref);
    render();
    return;
  }
  sel = tr.dataset.id;
  render();
});
["q","esquema","tipo","capa","pend"].forEach(id => {
  document.getElementById(id).addEventListener("input", render);
  document.getElementById(id).addEventListener("change", render);
});
render();
</script>
</body>
</html>
"""


def main() -> None:
    if not CANVAS.exists():
        raise SystemExit(f"No esta el canvas: {CANVAS}")
    objs = extraer_objetos(CANVAS.read_text(encoding="utf-8"))
    html = HTML.replace("__DATA__", json.dumps(objs, ensure_ascii=False))
    OUT.write_text(html, encoding="utf-8")
    print(f"{len(objs)} objetos -> {OUT}")


if __name__ == "__main__":
    main()

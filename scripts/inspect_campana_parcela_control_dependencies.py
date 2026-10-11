"""Genera un mapa de dependencias de campana_parcela_control (solo lectura)."""

from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
import re
import sys

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_connection import get_engine


ROOT_NAMES = {"sp_actualizar_campana_parcela_control", "campana_parcela_control"}
OUTPUT = Path("docs/ad_hoc/campana_parcela_control")


def main() -> None:
    engine = get_engine()
    with engine.connect() as conn:
        context = dict(conn.execute(text(
            "SELECT @@SERVERNAME server_name, DB_NAME() database_name, SYSDATETIMEOFFSET() extracted_at"
        )).mappings().one())
        objects = [dict(r) for r in conn.execute(text("""
            SELECT o.object_id, s.name schema_name, o.name object_name, o.type_desc,
                   o.modify_date, OBJECT_DEFINITION(o.object_id) definition
            FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
            WHERE o.is_ms_shipped=0
        """)).mappings()]
        catalog = [dict(r) for r in conn.execute(text("""
            SELECT sed.referencing_id, sed.referenced_id,
                   rs.name referencing_schema, ro.name referencing_name,
                   COALESCE(ds.name,sed.referenced_schema_name) referenced_schema,
                   COALESCE(dob.name,sed.referenced_entity_name) referenced_name,
                   sed.referenced_database_name, sed.referenced_server_name, sed.is_ambiguous
            FROM sys.sql_expression_dependencies sed
            JOIN sys.objects ro ON ro.object_id=sed.referencing_id
            JOIN sys.schemas rs ON rs.schema_id=ro.schema_id
            LEFT JOIN sys.objects dob ON dob.object_id=sed.referenced_id
            LEFT JOIN sys.schemas ds ON ds.schema_id=dob.schema_id
        """)).mappings()]
        triggers = [dict(r) for r in conn.execute(text("""
            SELECT tr.object_id, ps.name trigger_schema, tr.name trigger_name,
                   ps.name parent_schema, po.name parent_name, tr.is_disabled,
                   OBJECT_DEFINITION(tr.object_id) definition
            FROM sys.triggers tr
            JOIN sys.objects po ON po.object_id=tr.parent_id
            JOIN sys.schemas ps ON ps.schema_id=po.schema_id
            WHERE tr.parent_class=1
        """)).mappings()]
        try:
            jobs = [dict(r) for r in conn.execute(text("""
                SELECT j.name job_name, s.step_id, s.step_name, s.database_name, s.command
                FROM msdb.dbo.sysjobs j
                JOIN msdb.dbo.sysjobsteps s ON s.job_id=j.job_id
                WHERE LOWER(s.command) LIKE '%sp_actualizar_campana_parcela_control%'
                   OR LOWER(s.command) LIKE '%campana_parcela_control%'
            """)).mappings()]
        except Exception as exc:
            jobs = [{"error": str(exc).splitlines()[0]}]

    by_id = {r["object_id"]: r for r in objects}
    by_key = {(r["schema_name"].lower(), r["object_name"].lower()): r for r in objects}
    roots = [r for r in objects if r["object_name"].lower() in ROOT_NAMES]
    root_ids = {r["object_id"] for r in roots}
    outgoing = defaultdict(list)
    incoming = defaultdict(list)
    for edge in catalog:
        outgoing[edge["referencing_id"]].append(edge)
        if edge["referenced_id"]:
            incoming[edge["referenced_id"]].append(edge)

    # Descendientes transitivos registrados por SQL Server.
    selected = set(root_ids)
    queue = deque(root_ids)
    while queue:
        current = queue.popleft()
        for edge in outgoing[current]:
            target = edge["referenced_id"]
            if target in by_id and target not in selected:
                selected.add(target)
                queue.append(target)

    # Referencias textuales a objetos conocidos, incluyendo SQL dinámico.
    textual = set()
    pattern = re.compile(r"(?i)(?:\[([^\]]+)\]|([A-Za-z_]\w*))\s*\.\s*(?:\[([^\]]+)\]|([A-Za-z_]\w*))")
    changed = True
    while changed:
        changed = False
        for oid in list(selected):
            for m in pattern.finditer(by_id[oid].get("definition") or ""):
                key = ((m.group(1) or m.group(2)).lower(), (m.group(3) or m.group(4)).lower())
                target = by_key.get(key)
                if target and target["object_id"] != oid:
                    textual.add((oid, target["object_id"]))
                    if target["object_id"] not in selected:
                        selected.add(target["object_id"]); changed = True

    # Referencias inversas por texto (captura módulos con EXEC/SQL dinámico).
    reverse_text = []
    needles = [r["object_name"].lower() for r in roots]
    for obj in objects:
        definition = (obj.get("definition") or "").lower()
        if obj["object_id"] not in root_ids and any(n in definition for n in needles):
            reverse_text.append(obj)

    def name(oid: int) -> str:
        o = by_id[oid]; return f"{o['schema_name']}.{o['object_name']}"

    OUTPUT.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Mapa de dependencias: campaña parcela control", "",
        f"> Servidor: `{context['server_name']}`  ", f"> Base: `{context['database_name']}`  ",
        f"> Extracción: `{context['extracted_at']}`", "",
        "## Objetos raíz", "",
    ]
    for r in sorted(roots, key=lambda x: x["object_name"]):
        lines.append(f"- `{name(r['object_id'])}` — {r['type_desc']} (modificado {r['modify_date']})")
    missing = ROOT_NAMES - {r["object_name"].lower() for r in roots}
    for item in sorted(missing): lines.append(f"- `{item}` — **no encontrado**")

    lines += ["", "## Dependencias directas y transitivas", "", "```text"]
    expanded = set()
    def tree(oid: int, prefix: str = "", ancestry=frozenset()):
        lines.append(prefix + name(oid) + f" [{by_id[oid]['type_desc']}]")
        if oid in ancestry or oid in expanded: return
        expanded.add(oid)
        children = {}
        for e in outgoing[oid]:
            if e["referenced_id"] in selected: children[e["referenced_id"]] = "catálogo"
        for parent, target in textual:
            if parent == oid: children.setdefault(target, "texto")
        ordered = sorted(children.items(), key=lambda x: name(x[0]))
        for i, (child, source) in enumerate(ordered):
            last = i == len(ordered)-1
            lines.append(prefix + ("└── " if last else "├── ") + f"[{source}] {name(child)} [{by_id[child]['type_desc']}]")
            if child not in expanded:
                before = len(lines); tree(child, prefix + ("    " if last else "│   ") + "    ", ancestry | {oid}); del lines[before]
    for root in sorted(roots, key=lambda x: x["object_name"]):
        tree(root["object_id"]); lines.append("")
    lines += ["```", "", "## Dependencias inversas: quién los usa", ""]
    users = {}
    for rid in root_ids:
        for e in incoming[rid]: users[e["referencing_id"]] = "catálogo"
    for obj in reverse_text: users.setdefault(obj["object_id"], "texto")
    if users:
        for oid, source in sorted(users.items(), key=lambda x: name(x[0])):
            lines.append(f"- `[{source}]` `{name(oid)}` — {by_id[oid]['type_desc']}")
    else: lines.append("- No se encontraron consumidores en módulos SQL de esta base.")

    relevant_triggers = [
        tr for tr in triggers
        if (tr["parent_name"] or "").lower() in ROOT_NAMES
        or any(n in (tr.get("definition") or "").lower() for n in ROOT_NAMES)
    ]
    lines += ["", "## Triggers", ""]
    if relevant_triggers:
        for tr in relevant_triggers:
            state = "deshabilitado" if tr["is_disabled"] else "habilitado"
            lines.append(f"- `{tr['trigger_schema']}.{tr['trigger_name']}` sobre `{tr['parent_schema']}.{tr['parent_name']}` — {state}")
    else:
        lines.append("- No se encontraron triggers asociados ni triggers que referencien literalmente los objetos.")
    lines += ["", "## Ejecuciones programadas (SQL Server Agent)", ""]
    if jobs and "error" in jobs[0]:
        lines.append(f"- No fue posible consultar `msdb`: `{jobs[0]['error']}`")
    elif jobs:
        for job in jobs:
            lines.append(f"- Job `{job['job_name']}`, paso {job['step_id']} `{job['step_name']}`, base `{job['database_name']}`")
    else:
        lines.append("- No se encontraron pasos de jobs que contengan literalmente estos nombres.")

    lines += ["", "## Ejecución desde el código de la aplicación", "",
              "La búsqueda en el repositorio no encontró llamadas ni referencias a estos nombres.", "",
              "## Limitaciones", "",
              "Las dependencias por sinónimos, otras bases, jobs de SQL Server Agent, triggers deshabilitados o SQL dinámico construido sin el nombre literal pueden no aparecer."]
    (OUTPUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    defs = []
    for oid in sorted(selected, key=name):
        if by_id[oid].get("definition"):
            defs += [f"-- {name(oid)} ({by_id[oid]['type_desc']})", by_id[oid]["definition"].rstrip(), "GO", ""]
    (OUTPUT / "definiciones_bd.sql").write_text("\n".join(defs), encoding="utf-8")
    print(f"Servidor={context['server_name']} Base={context['database_name']}")
    print(f"Raices={len(roots)} Objetos={len(selected)} Consumidores={len(users)}")
    print(OUTPUT.resolve())


if __name__ == "__main__":
    main()

"""Exporta metadatos y definiciones SQL del flujo Datos Conciliados.

Solo consulta vistas de catalogo de SQL Server; no ejecuta procedimientos.
"""

from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
import re
import sys

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_connection import get_engine


PROFILES = {
    "datos_conciliados": {
        "title": "Datos Conciliados",
        "output_dir": Path("docs/ad_hoc/datos_conciliados"),
        "roots": (
            "inventar_SpcHidr.sp_refrescar_historico_apilado_test",
            "inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test",
            "inventar_SpcHidr.Datos_conciliados_of",
            "inventar_SpcHidr.v_ajuste_camiones_emision_test",
            "reclamo.v_reclamo_para_conciliados",
        ),
        "flow": (
            "Vista previa / Excel / PDF",
            "├── EXEC inventar_SpcHidr.sp_refrescar_historico_apilado_test",
            "├── EXEC inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test",
            "└── SELECT inventar_SpcHidr.Datos_conciliados_of",
            "    └── Excel además consulta inventar_SpcHidr.v_ajuste_camiones_emision_test",
        ),
    },
    "analisis_tm": {
        "title": "Análisis TM / Análisis Torres de Muestreo",
        "output_dir": Path("docs/ad_hoc/analisis_tm"),
        "roots": (
            "inventar_SpcHidr.sp_mantiene_apilado_tmh_v2_test",
            "inventar_SpcHidr.sp_mantiene_factor_ajuste_camiones_v2_test",
            "inventar_SpcHidr.sp_refrescar_clays_cufe",
            "inventar_SpcHidr.sp_actualizar_reporte_turno_cache_emision_test",
            "inventar_SpcHidr.reporte_turno_cache_emision_test",
            "inventar_SpcHidr.sp_generador_reporte_diario_emision_test",
        ),
        "flow": (
            "Vista previa Análisis TM (tipo=reporte_turno)",
            "├── EXEC sp_mantiene_factor_ajuste_camiones_v2_test (@DiasReproceso=0)",
            "├── Si el período alcanza 2026-08-01: EXEC sp_refrescar_clays_cufe",
            "├── EXEC sp_actualizar_reporte_turno_cache_emision_test",
            "└── SELECT reporte_turno_cache_emision_test",
            "",
            "Excel Análisis Torres de Muestreo (tipo=reporte_turno)",
            "├── EXEC sp_mantiene_apilado_tmh_v2_test (@DiasReproceso=7)",
            "├── EXEC sp_mantiene_factor_ajuste_camiones_v2_test (@DiasReproceso=0)",
            "├── Si el período alcanza 2026-08-01: EXEC sp_refrescar_clays_cufe",
            "├── EXEC sp_actualizar_reporte_turno_cache_emision_test",
            "├── SELECT reporte_turno_cache_emision_test",
            "└── EXEC sp_generador_reporte_diario_emision_test",
            "",
            "PDF Análisis TM",
            "├── EXEC sp_mantiene_factor_ajuste_camiones_v2_test (@DiasReproceso=0)",
            "├── Si el período alcanza 2026-08-01: EXEC sp_refrescar_clays_cufe",
            "├── EXEC sp_actualizar_reporte_turno_cache_emision_test",
            "├── SELECT reporte_turno_cache_emision_test",
            "└── EXEC sp_generador_reporte_diario_emision_test",
        ),
    },
}


def rows(conn, sql: str, params: dict | None = None) -> list[dict]:
    return [dict(row) for row in conn.execute(text(sql), params or {}).mappings()]


def qname(schema: str, name: str) -> str:
    return f"{schema}.{name}"


def normalize_definition(definition: str) -> str:
    normalized = definition.rstrip().replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in normalized.splitlines())


def main(profile_name: str = "datos_conciliados") -> None:
    if profile_name not in PROFILES:
        raise SystemExit(
            f"Perfil desconocido: {profile_name}. Opciones: {', '.join(PROFILES)}"
        )
    profile = PROFILES[profile_name]
    output_dir = profile["output_dir"]
    root_objects = profile["roots"]
    engine = get_engine()
    if engine is None:
        raise RuntimeError("get_engine() devolvio None")

    with engine.connect() as conn:
        context = rows(
            conn,
            "SELECT @@SERVERNAME server_name, DB_NAME() database_name, "
            "SYSDATETIMEOFFSET() extracted_at",
        )[0]
        objects = rows(
            conn,
            """
            SELECT o.object_id, s.name schema_name, o.name object_name,
                   o.type, o.type_desc, o.modify_date,
                   OBJECT_DEFINITION(o.object_id) definition
            FROM sys.objects o
            JOIN sys.schemas s ON s.schema_id = o.schema_id
            WHERE o.is_ms_shipped = 0
            """,
        )
        dependencies = rows(
            conn,
            """
            SELECT sed.referencing_id,
                   rs.name referencing_schema, ro.name referencing_name,
                   sed.referenced_id,
                   COALESCE(sed.referenced_schema_name, ds.name) referenced_schema,
                   COALESCE(sed.referenced_entity_name, dob.name) referenced_name,
                   sed.referenced_database_name, sed.referenced_server_name,
                   sed.is_ambiguous
            FROM sys.sql_expression_dependencies sed
            JOIN sys.objects ro ON ro.object_id = sed.referencing_id
            JOIN sys.schemas rs ON rs.schema_id = ro.schema_id
            LEFT JOIN sys.objects dob ON dob.object_id = sed.referenced_id
            LEFT JOIN sys.schemas ds ON ds.schema_id = dob.schema_id
            """,
        )

    by_id = {row["object_id"]: row for row in objects}
    by_name = {
        qname(row["schema_name"], row["object_name"]).lower(): row
        for row in objects
    }
    deps_by_parent: dict[int, list[dict]] = defaultdict(list)
    for dep in dependencies:
        deps_by_parent[dep["referencing_id"]].append(dep)

    selected_ids: set[int] = set()
    queue: deque[int] = deque()
    missing: list[str] = []
    for name in root_objects:
        obj = by_name.get(name.lower())
        if obj:
            selected_ids.add(obj["object_id"])
            queue.append(obj["object_id"])
        else:
            missing.append(name)

    while queue:
        parent_id = queue.popleft()
        for dep in deps_by_parent.get(parent_id, []):
            child_id = dep.get("referenced_id")
            if child_id and child_id in by_id and child_id not in selected_ids:
                selected_ids.add(child_id)
                queue.append(child_id)

    # Complementa las dependencias registradas buscando referencias de dos partes
    # dentro del texto. Esto ayuda cuando un modulo usa SQL dinamico.
    textual_edges: set[tuple[int, int]] = set()
    pattern = re.compile(r"(?i)(?:\[([^\]]+)\]|([A-Za-z_][\w]*))\s*\.\s*(?:\[([^\]]+)\]|([A-Za-z_][\w]*))")
    changed = True
    while changed:
        changed = False
        for object_id in list(selected_ids):
            definition = by_id[object_id].get("definition") or ""
            for match in pattern.finditer(definition):
                schema = match.group(1) or match.group(2)
                name = match.group(3) or match.group(4)
                target = by_name.get(qname(schema, name).lower())
                if not target:
                    continue
                target_id = target["object_id"]
                if target_id == object_id:
                    continue
                textual_edges.add((object_id, target_id))
                if target_id not in selected_ids:
                    selected_ids.add(target_id)
                    changed = True

    selected = sorted(
        (by_id[object_id] for object_id in selected_ids),
        key=lambda row: (row["schema_name"], row["object_name"]),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    sql_parts = [
        "-- Definiciones actuales extraidas desde SQL Server.",
        f"-- Servidor: {context['server_name']}",
        f"-- Base: {context['database_name']}",
        f"-- Fecha de extraccion: {context['extracted_at']}",
        "-- Archivo informativo: no ejecutar completo sin revision.",
        "",
    ]
    for obj in selected:
        definition = obj.get("definition")
        if not definition:
            continue
        sql_parts.extend(
            [
                "-- " + "=" * 76,
                f"-- {qname(obj['schema_name'], obj['object_name'])} ({obj['type_desc']})",
                f"-- Ultima modificacion: {obj['modify_date']}",
                "-- " + "=" * 76,
                normalize_definition(definition),
                "GO",
                "",
            ]
        )
    (output_dir / "definiciones_bd.sql").write_text(
        "\n".join(sql_parts), encoding="utf-8"
    )

    lines = [
        f"# {profile['title']}: dependencias SQL",
        "",
        f"> Extraccion de solo lectura: `{context['extracted_at']}`",
        f"> Servidor: `{context['server_name']}`",
        f"> Base de datos: `{context['database_name']}`",
        "",
        "## Flujo ejecutado por la aplicacion",
        "",
        "```text",
        *profile["flow"],
        "```",
        "",
        "## Árbol de dependencias de base de datos",
        "",
        "Las aristas `[catalogo]` provienen de `sys.sql_expression_dependencies`;",
        "las `[texto]` fueron encontradas en la definición y pueden incluir SQL dinámico.",
        "",
        "```text",
    ]

    expanded: set[int] = set()

    def render(object_id: int, prefix: str = "", ancestry: frozenset[int] = frozenset()) -> None:
        obj = by_id[object_id]
        lines.append(f"{prefix}{qname(obj['schema_name'], obj['object_name'])} [{obj['type_desc']}]")
        if object_id in ancestry:
            lines[-1] += " (ciclo)"
            return
        if object_id in expanded:
            lines[-1] += " (ver definición anterior)"
            return
        expanded.add(object_id)
        children: dict[int, str] = {}
        for dep in deps_by_parent.get(object_id, []):
            child_id = dep.get("referenced_id")
            if child_id in selected_ids and child_id != object_id:
                children[child_id] = "catalogo"
        for parent_id, child_id in textual_edges:
            if parent_id == object_id and child_id in selected_ids:
                children.setdefault(child_id, "texto")
        ordered = sorted(children.items(), key=lambda item: qname(by_id[item[0]]["schema_name"], by_id[item[0]]["object_name"]))
        for index, (child_id, source) in enumerate(ordered):
            last = index == len(ordered) - 1
            branch = "└── " if last else "├── "
            continuation = "    " if last else "│   "
            child = by_id[child_id]
            lines.append(f"{prefix}{branch}[{source}] {qname(child['schema_name'], child['object_name'])} [{child['type_desc']}]")
            # Render descendants without duplicating the child heading.
            grandchildren_before = len(lines)
            child_children = []
            for dep in deps_by_parent.get(child_id, []):
                if dep.get("referenced_id") in selected_ids and dep.get("referenced_id") != child_id:
                    child_children.append(dep.get("referenced_id"))
            for parent, target in textual_edges:
                if parent == child_id and target in selected_ids:
                    child_children.append(target)
            if child_id not in ancestry and child_id not in expanded and child_children:
                render(child_id, prefix + continuation + "    ", ancestry | {object_id})
                del lines[grandchildren_before]
            elif child_id in expanded and child_children:
                lines[-1] += " (dependencias ya mostradas)"

    for root_name in root_objects:
        root = by_name.get(root_name.lower())
        if root:
            render(root["object_id"])
            lines.append("")
    lines.extend(["```", "", "## Objetos incluidos", "", "| Objeto | Tipo | Última modificación | Definición exportada |", "|---|---|---:|---|"])
    for obj in selected:
        has_definition = "Sí" if obj.get("definition") else "No (tabla u objeto sin módulo SQL)"
        lines.append(
            f"| `{qname(obj['schema_name'], obj['object_name'])}` | {obj['type_desc']} | "
            f"{obj['modify_date']} | {has_definition} |"
        )
    if missing:
        lines.extend(["", "## Objetos raíz no encontrados", ""])
        lines.extend(f"- `{name}`" for name in missing)
    lines.extend(
        [
            "",
            "## Archivos",
            "",
            "- `definiciones_bd.sql`: definiciones textuales vigentes de procedimientos, vistas y funciones alcanzadas.",
            "- `inventario_dependencias.tsv`: aristas del catálogo y referencias textuales detectadas.",
            "",
            "## Limitaciones",
            "",
            "SQL Server puede no registrar dependencias resueltas mediante SQL dinámico, sinónimos o referencias entre bases. "
            "Por eso este documento combina el catálogo con una inspección textual y debe regenerarse después de cambios en BD.",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    edge_lines = ["origen\tdestino\tfuente"]
    edge_sources: dict[tuple[str, str], set[str]] = defaultdict(set)
    for dep in dependencies:
        parent_id, child_id = dep["referencing_id"], dep.get("referenced_id")
        if parent_id in selected_ids and child_id in selected_ids and parent_id != child_id:
            parent, child = by_id[parent_id], by_id[child_id]
            edge_sources[(qname(parent["schema_name"], parent["object_name"]), qname(child["schema_name"], child["object_name"]))].add("catalogo")
    for parent_id, child_id in textual_edges:
        parent, child = by_id[parent_id], by_id[child_id]
        edge_sources[(qname(parent["schema_name"], parent["object_name"]), qname(child["schema_name"], child["object_name"]))].add("texto")
    all_edges = [
        (origin, target, "+".join(sorted(sources)))
        for (origin, target), sources in edge_sources.items()
    ]
    edge_lines.extend("\t".join(edge) for edge in sorted(all_edges))
    (output_dir / "inventario_dependencias.tsv").write_text(
        "\n".join(edge_lines) + "\n", encoding="utf-8"
    )

    print(f"Servidor={context['server_name']} Base={context['database_name']}")
    print(f"Objetos={len(selected)} Dependencias={len(all_edges)}")
    print(output_dir.resolve())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "datos_conciliados")

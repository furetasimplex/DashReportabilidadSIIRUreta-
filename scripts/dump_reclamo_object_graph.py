"""Cierre transitivo read-only de objetos reclamo + fuentes externas."""
from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db_connection import get_engine

OUT = ROOT / "auditoria_reclamo"

APP_INVENTAR = {
    "disponible_rotopalas",
    "control_reclamo_diario",
    "control_reclamo_sulfuro_camiones_thm_diario",
    "modulo",
    "parcela",
    "sp_mantiene_datos_conciliados_emision_test",
}

PUBLICACION_SEEDS = {
    "sp_mantiene_datos_conciliados_emision_test",
    "sp_mantiene_datos_conciliados_of",
    "v_reclamo_camiones_por_modulo",
    "vista_reclamo_diario_calculado",
    "vw_Datos_conciliados_of_activo",
    "vw_datos_conciliados_publicacion_base",
    "vw_datos_conciliados_reporte",
}


def safe_select(sql: str) -> None:
    cleaned = re.sub(r"/\*.*?\*/|--[^\n]*", "", sql, flags=re.S).strip().upper()
    if not (cleaned.startswith("SELECT") or cleaned.startswith("WITH")):
        raise RuntimeError("Consulta no permitida por guardia read-only")
    banned = re.compile(r"\b(INSERT|UPDATE|DELETE|MERGE|TRUNCATE|DROP|ALTER|CREATE|EXEC(?:UTE)?)\b")
    if banned.search(cleaned):
        raise RuntimeError("Verbo de escritura detectado por guardia read-only")


def qname(esquema: str | None, objeto: str | None) -> str:
    return f"{esquema or '?'}.{objeto or '?'}"


def main() -> None:
    engine = get_engine()
    extraido = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    with engine.connect() as conn:
        meta = pd.read_sql(
            text(
                "SELECT DB_NAME() AS database_actual, SUSER_SNAME() AS usuario, @@SERVERNAME AS servidor"
            ),
            conn,
        ).iloc[0].to_dict()

        objs_sql = """
        SELECT o.object_id, s.name AS esquema, o.name AS objeto, o.type_desc,
               o.create_date, o.modify_date
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id = o.schema_id
        WHERE o.type IN ('U','V','P','FN','IF','TF','TR')
          AND (
                s.name = 'reclamo'
             OR (s.name = 'inventar_SpcHidr' AND o.name IN (
                    'disponible_rotopalas',
                    'control_reclamo_diario',
                    'control_reclamo_sulfuro_camiones_thm_diario',
                    'control_medicion_topografia_diaria',
                    'modulo',
                    'parcela',
                    'modulos_turnos',
                    'datos_filtrados',
                    'vista_resumen_datos_filtrados',
                    'v_contingencia_totalizador_resuelto_operacional_test',
                    'sp_mantiene_datos_conciliados_emision_test',
                    'sp_mantiene_datos_conciliados_of',
                    'v_reclamo_camiones_por_modulo',
                    'vista_reclamo_diario_calculado',
                    'vw_Datos_conciliados_of_activo',
                    'vw_datos_conciliados_publicacion_base',
                    'vw_datos_conciliados_reporte',
                    'Datos_conciliados_of'
                ))
          )
        ORDER BY s.name, o.type_desc, o.name
        """
        safe_select(objs_sql)
        objs = pd.read_sql(text(objs_sql), conn)

        deps_sql = """
        SELECT d.referencing_id,
               OBJECT_SCHEMA_NAME(d.referencing_id) AS esquema_origen,
               OBJECT_NAME(d.referencing_id) AS objeto_origen,
               d.referenced_id,
               d.referenced_database_name AS db_destino,
               d.referenced_schema_name AS esquema_destino,
               d.referenced_entity_name AS objeto_destino,
               CASE WHEN d.referenced_id IS NULL THEN 1 ELSE 0 END AS unresolved
        FROM sys.sql_expression_dependencies d
        WHERE OBJECT_SCHEMA_NAME(d.referencing_id) IN ('reclamo','inventar_SpcHidr')
        """
        safe_select(deps_sql)
        deps = pd.read_sql(text(deps_sql), conn)

        types_sql = """
        SELECT o.object_id, s.name AS esquema, o.name AS objeto, o.type_desc
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id = o.schema_id
        WHERE o.type IN ('U','V','P','FN','IF','TF','TR')
        """
        safe_select(types_sql)
        types = pd.read_sql(text(types_sql), conn)

        fk_sql = """
        SELECT fk.name AS FK,
               OBJECT_SCHEMA_NAME(fk.parent_object_id) AS esquema_hijo,
               OBJECT_NAME(fk.parent_object_id) AS tabla_hijo,
               OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS esquema_padre,
               OBJECT_NAME(fk.referenced_object_id) AS tabla_padre
        FROM sys.foreign_keys fk
        WHERE OBJECT_SCHEMA_NAME(fk.parent_object_id) IN ('reclamo','inventar_SpcHidr')
           OR OBJECT_SCHEMA_NAME(fk.referenced_object_id) IN ('reclamo','inventar_SpcHidr')
        """
        safe_select(fk_sql)
        fks = pd.read_sql(text(fk_sql), conn)

        consumers_sql = """
        SELECT OBJECT_SCHEMA_NAME(d.referencing_id) AS esquema_origen,
               OBJECT_NAME(d.referencing_id) AS objeto_origen,
               o.type_desc AS tipo_origen,
               d.referenced_schema_name AS esquema_destino,
               d.referenced_entity_name AS objeto_destino
        FROM sys.sql_expression_dependencies d
        JOIN sys.objects o ON o.object_id = d.referencing_id
        WHERE d.referenced_schema_name = 'reclamo'
          AND OBJECT_SCHEMA_NAME(d.referencing_id) <> 'reclamo'
        ORDER BY esquema_origen, objeto_origen, objeto_destino
        """
        safe_select(consumers_sql)
        consumers = pd.read_sql(text(consumers_sql), conn)

    type_by_name = {
        qname(r.esquema, r.objeto): r.type_desc for r in types.itertuples(index=False)
    }
    type_by_id = {int(r.object_id): r.type_desc for r in types.itertuples(index=False)}

    edges: list[dict] = []
    outbound: dict[str, set[str]] = defaultdict(set)
    for r in deps.itertuples(index=False):
        src = qname(r.esquema_origen, r.objeto_origen)
        dst_schema = r.esquema_destino
        dst_obj = r.objeto_destino
        if not dst_obj:
            continue
        dst = qname(dst_schema, dst_obj)
        dst_type = type_by_id.get(int(r.referenced_id)) if pd.notna(r.referenced_id) else type_by_name.get(dst)
        if dst_type is None:
            dst_type = "UNRESOLVED"
        outbound[src].add(dst)
        edges.append(
            {
                "esquema_origen": r.esquema_origen,
                "objeto_origen": r.objeto_origen,
                "esquema_destino": dst_schema,
                "objeto_destino": dst_obj,
                "tipo_destino": dst_type,
                "db_destino": r.db_destino if pd.notna(r.db_destino) else "",
                "unresolved": int(r.unresolved),
            }
        )

    seeds = [qname(r.esquema, r.objeto) for r in objs.itertuples(index=False) if r.esquema == "reclamo"]
    seeds += [
        qname("inventar_SpcHidr", n)
        for n in sorted(APP_INVENTAR | PUBLICACION_SEEDS | {"Datos_conciliados_of", "control_medicion_topografia_diaria", "modulos_turnos", "datos_filtrados", "vista_resumen_datos_filtrados", "v_contingencia_totalizador_resuelto_operacional_test"})
        if qname("inventar_SpcHidr", n) in type_by_name or True
    ]

    reached: dict[str, dict] = {}
    queue: deque[tuple[str, int, str]] = deque()
    for s in seeds:
        if s not in reached:
            esquema, objeto = s.split(".", 1)
            reached[s] = {
                "esquema": esquema,
                "objeto": objeto,
                "tipo": type_by_name.get(s, "SEED_AUSENTE"),
                "nivel": 0,
                "via": "seed",
            }
            queue.append((s, 0, "seed"))

    while queue:
        src, nivel, _via = queue.popleft()
        if nivel >= 8:
            continue
        for dst in sorted(outbound.get(src, ())):
            if dst in reached:
                continue
            esquema, objeto = dst.split(".", 1) if "." in dst else ("?", dst)
            tipo = type_by_name.get(dst, "UNRESOLVED")
            # No expandir SPs inventar ajenos al paquete (balance, factor, etc.)
            if esquema == "inventar_SpcHidr" and tipo == "SQL_STORED_PROCEDURE":
                if objeto not in PUBLICACION_SEEDS and objeto not in APP_INVENTAR:
                    reached[dst] = {
                        "esquema": esquema,
                        "objeto": objeto,
                        "tipo": tipo,
                        "nivel": nivel + 1,
                        "via": src,
                    }
                    continue
            reached[dst] = {
                "esquema": esquema,
                "objeto": objeto,
                "tipo": tipo,
                "nivel": nivel + 1,
                "via": src,
            }
            queue.append((dst, nivel + 1, src))

    # FK de tablas alcanzadas
    reached_tables = {
        qname(r["esquema"], r["objeto"])
        for r in reached.values()
        if r["tipo"] == "USER_TABLE"
    }
    fk_rows = []
    for r in fks.itertuples(index=False):
        hijo = qname(r.esquema_hijo, r.tabla_hijo)
        padre = qname(r.esquema_padre, r.tabla_padre)
        if hijo in reached_tables or padre in reached_tables:
            fk_rows.append(
                {
                    "FK": r.FK,
                    "esquema_hijo": r.esquema_hijo,
                    "tabla_hijo": r.tabla_hijo,
                    "esquema_padre": r.esquema_padre,
                    "tabla_padre": r.tabla_padre,
                }
            )
            if padre not in reached:
                reached[padre] = {
                    "esquema": r.esquema_padre,
                    "objeto": r.tabla_padre,
                    "tipo": type_by_name.get(padre, "USER_TABLE"),
                    "nivel": 99,
                    "via": f"FK:{hijo}",
                }

    def accion(row: dict) -> str:
        esq, tipo, obj = row["esquema"], row["tipo"], row["objeto"]
        if tipo == "SEED_AUSENTE":
            return "no_existe_en_prod"
        if esq == "reclamo" and tipo == "USER_TABLE":
            return "copiar_schema_y_datos"
        if esq == "reclamo":
            return "copiar_definicion"
        if esq == "inventar_SpcHidr" and tipo == "USER_TABLE":
            return "copiar_schema_y_datos_o_sinonimo"
        if esq == "inventar_SpcHidr" and tipo == "VIEW":
            return "copiar_definicion_o_materializar"
        if esq == "inventar_SpcHidr" and tipo == "SQL_STORED_PROCEDURE":
            return "copiar_si_publica"
        if esq in ("sys",):
            return "ignorar"
        return "revisar"

    def paquete(row: dict) -> str:
        esq, obj, tipo = row["esquema"], row["objeto"], row["tipo"]
        if esq == "reclamo":
            if obj.endswith("_contingencia_test"):
                return "C_contingencia"
            return "A_nucleo_reclamo"
        if obj in APP_INVENTAR or obj in {
            "control_medicion_topografia_diaria",
            "modulos_turnos",
            "datos_filtrados",
            "vista_resumen_datos_filtrados",
        }:
            return "B_fuentes_etl"
        if obj in PUBLICACION_SEEDS or obj == "Datos_conciliados_of":
            return "D_publicacion"
        if "contingencia" in (obj or "").lower():
            return "C_contingencia"
        return "E_colateral"

    catalog_rows = []
    for key, row in sorted(reached.items()):
        catalog_rows.append(
            {
                "paquete": paquete(row),
                "accion": accion(row),
                "esquema": row["esquema"],
                "objeto": row["objeto"],
                "tipo": row["tipo"],
                "nivel_desde_seed": row["nivel"],
                "via": row["via"],
            }
        )
    catalog = pd.DataFrame(catalog_rows).sort_values(
        ["paquete", "esquema", "tipo", "objeto"]
    )

    # Edges only among reached objects (plus origin in reclamo)
    edge_rows = []
    seen = set()
    for e in edges:
        src = qname(e["esquema_origen"], e["objeto_origen"])
        dst = qname(e["esquema_destino"], e["objeto_destino"])
        if src in reached or (e["esquema_origen"] == "reclamo"):
            tup = (src, dst)
            if tup in seen:
                continue
            seen.add(tup)
            if dst in reached or e["esquema_origen"] == "reclamo":
                edge_rows.append(e)
    edges_df = pd.DataFrame(edge_rows).drop_duplicates()
    if not edges_df.empty:
        edges_df = edges_df.sort_values(
            ["esquema_origen", "objeto_origen", "esquema_destino", "objeto_destino"]
        )

    tables = catalog[catalog["tipo"] == "USER_TABLE"].copy()

    catalog.to_csv(OUT / "17_objetos_cierre.csv", index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    tables.to_csv(OUT / "17b_tablas.csv", index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    edges_df.to_csv(OUT / "17c_aristas.csv", index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    pd.DataFrame(fk_rows).to_csv(OUT / "17d_fk.csv", index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    consumers.to_csv(OUT / "17e_consumidores_externos.csv", index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    (OUT / "17_fuente.txt").write_text(
        (
            f"extraido={extraido}\n"
            f"database_actual={meta['database_actual']}\n"
            f"servidor={meta['servidor']}\n"
            f"objetos_cierre={len(catalog)}\n"
            f"tablas={len(tables)}\n"
            "script=scripts/dump_reclamo_object_graph.py\n"
        ),
        encoding="utf-8",
    )
    print(f"Fuente: {meta['database_actual']} @ {meta['servidor']}")
    print(tables.to_string(index=False))
    print("--- paquetes ---")
    print(catalog.groupby(["paquete", "tipo"]).size().to_string())


if __name__ == "__main__":
    main()

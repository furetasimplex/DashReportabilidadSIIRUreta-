"""Volcado read-only de vistas reclamo.* + catalogo para documentacion."""
from __future__ import annotations

import csv
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db_connection import get_engine

OUT = ROOT / "auditorias/archivo/auditoria_reclamo"
SQL_DEFS = OUT / "sql_definitions"

USO_PANTALLA = {
    "v_ajustes_aplicables": "cadena_calculo",
    "v_camiones_acumulado": "pantalla",
    "v_cuadratura_modulo": "pantalla",
    "v_cv25_diario": "cadena_calculo",
    "v_diferencia_cv25": "pantalla",
    "v_modulo_base": "pantalla",
    "v_preliminar_cv25": "cadena_calculo",
    "v_preliminar_cv25_con_acumulado": "cadena_calculo",
    "v_reclamo_diario": "pantalla",
    "v_reclamo_para_conciliados": "pantalla",
    "v_rendimiento_rotopala": "pantalla",
    "v_topografia_resuelta": "pantalla",
}


def safe_select(sql: str) -> None:
    cleaned = re.sub(r"/\*.*?\*/|--[^\n]*", "", sql, flags=re.S).strip().upper()
    if not (cleaned.startswith("SELECT") or cleaned.startswith("WITH")):
        raise RuntimeError("Consulta no permitida por guardia read-only")
    banned = re.compile(r"\b(INSERT|UPDATE|DELETE|MERGE|TRUNCATE|DROP|ALTER|CREATE|EXEC(?:UTE)?)\b")
    if banned.search(cleaned):
        raise RuntimeError("Verbo de escritura detectado por guardia read-only")


def sha256_text(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:16]


def uso(nombre: str) -> str:
    if nombre.endswith("_contingencia_test"):
        return "contingencia_test"
    return USO_PANTALLA.get(nombre, "no_clasificada")


def main() -> None:
    SQL_DEFS.mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    extraido = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    with engine.connect() as conn:
        meta_sql = """
        SELECT DB_NAME() AS database_actual, SUSER_SNAME() AS usuario, @@SERVERNAME AS servidor
        """
        safe_select(meta_sql)
        meta = pd.read_sql(text(meta_sql), conn).iloc[0].to_dict()

        views_sql = """
        SELECT s.name AS esquema, o.name AS objeto, o.type_desc,
               o.create_date, o.modify_date, sm.definition
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id = o.schema_id
        JOIN sys.sql_modules sm ON sm.object_id = o.object_id
        WHERE s.name = 'reclamo' AND o.type = 'V'
        ORDER BY o.name
        """
        safe_select(views_sql)
        views = pd.read_sql(text(views_sql), conn)

        cols_sql = """
        SELECT s.name AS esquema, o.name AS vista, c.column_id, c.name AS columna,
               ty.name AS tipo, c.max_length, c.precision, c.scale, c.is_nullable
        FROM sys.views o
        JOIN sys.schemas s ON s.schema_id = o.schema_id
        JOIN sys.columns c ON c.object_id = o.object_id
        JOIN sys.types ty ON ty.user_type_id = c.user_type_id
        WHERE s.name = 'reclamo'
        ORDER BY o.name, c.column_id
        """
        safe_select(cols_sql)
        cols = pd.read_sql(text(cols_sql), conn)

        deps_sql = """
        SELECT OBJECT_NAME(d.referencing_id) AS vista,
               d.referenced_schema_name AS esquema_destino,
               d.referenced_entity_name AS objeto_destino
        FROM sys.sql_expression_dependencies d
        JOIN sys.objects o ON o.object_id = d.referencing_id
        JOIN sys.schemas s ON s.schema_id = o.schema_id
        WHERE s.name = 'reclamo' AND o.type = 'V'
        ORDER BY vista, esquema_destino, objeto_destino
        """
        safe_select(deps_sql)
        deps = pd.read_sql(text(deps_sql), conn)

    catalog_rows = []
    for row in views.itertuples(index=False):
        definition = row.definition or "-- DEFINICION NO DISPONIBLE\n"
        path = SQL_DEFS / f"{row.esquema}.{row.objeto}.sql"
        previous = path.read_text(encoding="utf-8") if path.exists() else ""
        prev_hash = sha256_text(previous) if previous else ""
        new_hash = sha256_text(definition)
        if previous and prev_hash == new_hash:
            vs_repo = "igual"
        elif previous:
            vs_repo = "actualizada"
        else:
            vs_repo = "nueva"
        path.write_text(definition, encoding="utf-8")
        catalog_rows.append(
            {
                "esquema": row.esquema,
                "vista": row.objeto,
                "uso": uso(row.objeto),
                "create_date": row.create_date,
                "modify_date": row.modify_date,
                "sha256_16": new_hash,
                "vs_sql_definitions_previo": vs_repo,
                "archivo": f"sql_definitions/{row.esquema}.{row.objeto}.sql",
            }
        )

    catalog = pd.DataFrame(catalog_rows)
    catalog_path = OUT / "16_vistas_reclamo.csv"
    catalog.to_csv(catalog_path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    cols.to_csv(OUT / "16b_columnas_vistas.csv", index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    deps.to_csv(OUT / "16c_dependencias_vistas.csv", index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)

    (OUT / "16_vistas_fuente.txt").write_text(
        (
            f"extraido={extraido}\n"
            f"database_actual={meta['database_actual']}\n"
            f"servidor={meta['servidor']}\n"
            f"usuario={meta['usuario']}\n"
            f"vistas={len(catalog)}\n"
            "script=scripts/dump_reclamo_views.py\n"
        ),
        encoding="utf-8",
    )
    print(f"Fuente: {meta['database_actual']} @ {meta['servidor']}")
    print(catalog.to_string(index=False))
    print(f"Catalogo: {catalog_path}")


if __name__ == "__main__":
    main()

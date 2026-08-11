"""Inspecciona dos vistas hidro en la BD actual y DEV_SIIR (solo lectura)."""

from pathlib import Path
import hashlib
import sys

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_connection import get_engine


VIEWS = ("v_imp_chancado_normalizado", "v_imp_conciliacion_chancado")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def script_sql(definition: str, modified_at) -> str:
    definition = definition.replace("\r\n", "\n").strip()
    return (
        "-- Fuente: definición vigente en DEV_SIIR (sys.sql_modules).\n"
        f"-- Extraída: {modified_at}\n"
        "USE [DEV_SIIR];\n"
        "GO\n\n"
        f"{definition}\n"
        "GO\n"
    )


def main() -> None:
    engine = get_engine()
    with engine.connect() as conn:
        databases = [conn.scalar(text("SELECT DB_NAME()"))]
        if conn.scalar(text("SELECT DB_ID('DEV_SIIR')")) is not None:
            databases.append("DEV_SIIR")

        dev_definitions = {}
        for database in dict.fromkeys(databases):
            sql = text(
                f"""
                SELECT o.name, sm.definition, o.modify_date
                FROM [{database}].sys.objects AS o
                JOIN [{database}].sys.schemas AS s ON s.schema_id = o.schema_id
                JOIN [{database}].sys.sql_modules AS sm ON sm.object_id = o.object_id
                WHERE s.name = 'hidro'
                  AND o.name IN ('v_imp_chancado_normalizado',
                                 'v_imp_conciliacion_chancado')
                ORDER BY o.name
                """
            )
            found = {row.name: row for row in conn.execute(sql)}
            for name in VIEWS:
                row = found.get(name)
                if row is None:
                    print(f"{database}.hidro.{name}: NO ENCONTRADA")
                    continue
                digest = hashlib.sha256(row.definition.encode("utf-8")).hexdigest()[:16]
                print(
                    f"{database}.hidro.{name}: caracteres={len(row.definition)} "
                    f"sha256={digest} modificada={row.modify_date}"
                )
                if database == "DEV_SIIR":
                    dev_definitions[name] = row

    if "--write" not in sys.argv:
        return
    missing = [name for name in VIEWS if name not in dev_definitions]
    if missing:
        raise RuntimeError(f"No se exportarán archivos; faltan vistas: {missing}")

    combined = [
        "-- Vistas hidro vigentes utilizadas por Análisis TM.",
        "-- Fuente: DEV_SIIR.sys.sql_modules.",
        "",
    ]
    for name in VIEWS:
        row = dev_definitions[name]
        content = script_sql(row.definition, row.modify_date)
        for folder in ("docs/views", "docs/stored_procedures"):
            target = PROJECT_ROOT / folder / f"{name}.sql"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        combined.extend(
            [
                "-- " + "=" * 76,
                f"-- DEV_SIIR.hidro.{name}",
                "-- " + "=" * 76,
                "",
                content,
            ]
        )

    report_target = (
        PROJECT_ROOT
        / "docs/reportes/analisis_tm/definiciones_hidro_imp_chancado.sql"
    )
    report_target.parent.mkdir(parents=True, exist_ok=True)
    report_target.write_text("\n".join(combined), encoding="utf-8")
    print("Definiciones actualizadas en docs/views, docs/stored_procedures y reporte Análisis TM")


if __name__ == "__main__":
    main()

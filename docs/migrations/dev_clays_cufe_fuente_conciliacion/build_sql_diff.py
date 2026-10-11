from __future__ import annotations

import difflib
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise AssertionError(f"{label}: se esperaba 1 reemplazo y hubo {count}")
    return updated


def build_view(source: str) -> str:
    text = re.sub(r"^\s*CREATE\s+VIEW", "ALTER VIEW", source, count=1)
    text = replace_once(
        text,
        r"(TRY_CONVERT\(float, c\.CuFe\)\s+AS CuFe_MB)(\s+FROM \[inventar_SpcHidr\]\.\[v_conciliacion_chancado_v2\])",
        r"\1,\n\n        UPPER(LTRIM(RTRIM(ISNULL(c.Fuente_Dato, ''))))\n            AS Fuente_Conciliacion\2",
        "mb_base.Fuente_Conciliacion",
    )
    text = replace_once(
        text,
        r"(MAX\(CuFe_MB\)\s+AS CuFe_MB)(\s+FROM mb_base)",
        r"\1,\n\n        MAX(Fuente_Conciliacion)\n            AS Fuente_Conciliacion\2",
        "mb.Fuente_Conciliacion",
    )
    text = replace_once(
        text,
        r"(m\.CaolBeta_MB,\s+m\.CuFe_MB,)(\s+m\.Cantidad_Registros_MB)",
        r"\1\n        m.Fuente_Conciliacion,\2",
        "fuentes_propias.Fuente_Conciliacion",
    )
    text = replace_once(
        text,
        r"(f\.CaolBeta_MB,\s+f\.CuFe_MB,)(\s+f\.Cantidad_Registros_MB)",
        r"\1\n        f.Fuente_Conciliacion,\2",
        "fuentes_completas.Fuente_Conciliacion",
    )

    for analito, suffixes in {
        "CaolBeta": ("SIN_REPRESENTATIVIDAD", "NO_REPRESENTATIVO", "SIN_RESULTADO_NIR"),
        "CuFe": ("SIN_REPRESENTATIVIDAD", "NO_REPRESENTATIVO", "SIN_RESULTADO_CUFE"),
    }.items():
        for suffix in suffixes:
            text = replace_once(
                text,
                rf"(WHEN f\.{analito}_MB IS NOT NULL.*?THEN )'MB_{suffix}'",
                rf"\1CASE WHEN f.Fuente_Conciliacion = 'IMP' THEN 'IMP_{suffix}' ELSE 'MB_{suffix}' END",
                f"{analito}.{suffix}",
            )

    text = replace_once(
        text,
        r"(\s+CuFe_MB,)(\s+/\* Resultado con precisión completa \*/)",
        r"\1\n\n    Fuente_Conciliacion,\2",
        "SELECT final.Fuente_Conciliacion",
    )
    return text.rstrip() + "\n"


def build_sp(source: str) -> str:
    text = re.sub(r"^\s*CREATE\s+PROCEDURE", "ALTER PROCEDURE", source, count=1)
    text = replace_once(
        text,
        r"(\) AS CuFe_Anterior)(\s+INTO #destino)",
        r"\1,\n\n        hist.Fuente_CaolBeta\n            AS Fuente_CaolBeta_Anterior,\n\n        hist.Fuente_CuFe\n            AS Fuente_CuFe_Anterior\2",
        "destino.fuentes anteriores",
    )
    text = replace_once(
        text,
        r"(\) AS norm\s+\(\s+Torre_Normalizada,\s+Turno_Normalizado\s+\))(\s+WHERE\s+c\.Fecha BETWEEN)",
        r"\1\n\n    OUTER APPLY\n    (\n        SELECT TOP (1)\n            t.Fuente_CaolBeta,\n            t.Fuente_CuFe\n        FROM [inventar_SpcHidr].[Clays_CuFe_trazabilidad] AS t\n        WHERE t.Fecha = c.Fecha\n          AND t.Torre = CASE\n                WHEN norm.Torre_Normalizada IN ('TM1', 'T1', 'TORRE1') THEN 'TM1'\n                WHEN norm.Torre_Normalizada IN ('TM2', 'T2', 'TORRE2') THEN 'TM2'\n              END\n          AND t.Turno = CASE\n                WHEN norm.Turno_Normalizado IN ('A', 'TA', 'TURNOA') THEN 'A'\n                WHEN norm.Turno_Normalizado IN ('B', 'TB', 'TURNOB') THEN 'B'\n              END\n        ORDER BY t.fecha_proceso DESC, t.id_trazabilidad DESC\n    ) AS hist\2",
        "destino.OUTER APPLY historial",
    )
    text = replace_once(
        text,
        r"(d\.CaolBeta_Anterior,\s+d\.CuFe_Anterior,)",
        r"\1\n\n        d.Fuente_CaolBeta_Anterior,\n        d.Fuente_CuFe_Anterior,",
        "acciones.fuentes anteriores",
    )
    text = replace_once(
        text,
        r"(THEN 'ACTUALIZAR'\s+)(ELSE 'SIN_CAMBIO')",
        r"\1WHEN\n            (\n                d.Fuente_CaolBeta_Anterior IS NOT NULL\n                AND ISNULL(d.Fuente_CaolBeta_Anterior, '') <> ISNULL(f.Fuente_CaolBeta, '')\n            )\n            OR\n            (\n                d.Fuente_CuFe_Anterior IS NOT NULL\n                AND ISNULL(d.Fuente_CuFe_Anterior, '') <> ISNULL(f.Fuente_CuFe, '')\n            )\n                THEN 'TRAZABILIDAD'\n\n            \2",
        "accion ACTUALIZAR_TRAZABILIDAD",
    )
    text = text.replace(
        "                'ACTUALIZAR'\n\n            );",
        "                'ACTUALIZAR',\n\n                'TRAZABILIDAD'\n\n            );",
        1,
    )
    if "'TRAZABILIDAD'\n\n            );" not in text:
        raise AssertionError("No se amplió el INSERT de trazabilidad")
    text = replace_once(
        text,
        r"(\) AS Registros_Actualizados,)(\s+SUM\s+\(\s+CASE\s+WHEN Accion = 'SIN_CAMBIO')",
        r"\1\n\n        SUM\n        (\n            CASE\n                WHEN Accion = 'TRAZABILIDAD' THEN 1\n                ELSE 0\n            END\n        ) AS Registros_Trazabilidad_Actualizada,\2",
        "contador trazabilidad",
    )
    # La segunda lista es el resultado detallado; la primera ya se amplió arriba.
    text = text.replace(
        "            'INSERTAR',\n\n            'ACTUALIZAR'\n\n        )",
        "            'INSERTAR',\n\n            'ACTUALIZAR',\n\n            'TRAZABILIDAD'\n\n        )",
        1,
    )
    if text.count("TRAZABILIDAD") < 4:
        raise AssertionError("La acción de trazabilidad no quedó propagada completamente")
    return text.rstrip() + "\n"


def main() -> None:
    view_before = (HERE / "v_clays_cufe_calculado_v2_test.before.sql").read_text(encoding="utf-8-sig")
    sp_before = (HERE / "sp_refrescar_clays_cufe.before.sql").read_text(encoding="utf-8-sig")
    view_after = build_view(view_before)
    sp_after = build_sp(sp_before)

    (HERE / "v_clays_cufe_calculado_v2_test.after.sql").write_text(view_after, encoding="utf-8")
    (HERE / "sp_refrescar_clays_cufe.after.sql").write_text(sp_after, encoding="utf-8")
    deploy = "SET XACT_ABORT ON;\nBEGIN TRANSACTION;\n\n" + view_after + "\nGO\n\n" + sp_after + "\nGO\n\nCOMMIT TRANSACTION;\nGO\n"
    (HERE / "deploy_dev.sql").write_text(deploy, encoding="utf-8")

    chunks: list[str] = []
    for name, before, after in (
        ("v_clays_cufe_calculado_v2_test.sql", view_before, view_after),
        ("sp_refrescar_clays_cufe.sql", sp_before, sp_after),
    ):
        chunks.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True), f"a/{name}", f"b/{name}"))
    (HERE / "cambio_fuente_conciliacion.diff").write_text("".join(chunks), encoding="utf-8")


if __name__ == "__main__":
    main()

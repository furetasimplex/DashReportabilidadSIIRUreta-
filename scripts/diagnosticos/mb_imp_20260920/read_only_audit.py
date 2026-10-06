"""Read-only DEV snapshot for MB/IMP lineage around 2026-09-20."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine

HERE = Path(__file__).resolve().parent


def main():
    if os.getenv("SQLSERVER_DB", "").lower() != "inventar_spchidr":
        raise RuntimeError("Expected DEV inventar_SpcHidr")
    with get_engine().connect() as conn:
        def rows(sql):
            assert sql.lstrip().upper().startswith("SELECT")
            return [dict(row) for row in conn.execute(text(sql)).mappings()]

        identity = rows("SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name")
        if identity[0]["database_name"].lower() != "inventar_spchidr":
            raise RuntimeError(identity)
        queries = {
            "mov_cam_powerbi": """SELECT CAST(fecha AS date) AS Fecha, turno AS Turno,
                          COUNT(*) AS n, SUM(TRY_CONVERT(float,tonelaje_descarga_tms)) AS Ton,
                          SUM(TRY_CONVERT(float,tonelaje_descarga_tms)*TRY_CONVERT(float,cut_ponderado))
                          /NULLIF(SUM(TRY_CONVERT(float,tonelaje_descarga_tms)),0) AS CuT
                          FROM inventar_SpcHidr.mov_cam_powerbi
                          WHERE CAST(fecha AS date) BETWEEN '2026-09-19' AND '2026-09-21'
                          GROUP BY CAST(fecha AS date),turno ORDER BY Fecha,Turno""",
            "mov_cam": """SELECT CAST(Fecha AS date) AS Fecha, Turno, COUNT(*) AS n,
                        SUM(Ton) AS Ton, SUM(Ton*CuTG00)/NULLIF(SUM(Ton),0) AS CuT,
                        SUM(Ton*CusG01)/NULLIF(SUM(Ton),0) AS CuS,
                        SUM(Ton*CUFE)/NULLIF(SUM(Ton),0) AS CuFe,
                        SUM(Ton*C03G02)/NULLIF(SUM(Ton),0) AS CO3,
                        SUM(Ton*[100G07])/NULLIF(SUM(Ton),0) AS Malla100,
                        SUM(Ton*ClayBG10)/NULLIF(SUM(Ton),0) AS Clay_Beta
                        FROM inventar_SpcHidr.mov_cam
                        WHERE CAST(Fecha AS date) BETWEEN '2026-09-19' AND '2026-09-21'
                        GROUP BY CAST(Fecha AS date), Turno ORDER BY Fecha,Turno""",
            "official": """SELECT CAST(Fecha AS date) AS Fecha,
                     CASE WHEN Turno='TA' THEN 'A' WHEN Turno='TB' THEN 'B' ELSE Turno END AS Turno,
                     COUNT(*) AS n, SUM(Ton) AS Ton,
                     SUM(Ton*PONDCuTG00)/NULLIF(SUM(Ton),0) AS CuT,
                     SUM(Ton*PONDCusG01)/NULLIF(SUM(Ton),0) AS CuS,
                     SUM(Ton*PONDCUFE)/NULLIF(SUM(Ton),0) AS CuFe,
                     SUM(Ton*PONDC03G02)/NULLIF(SUM(Ton),0) AS CO3,
                     SUM(Ton*POND100G07)/NULLIF(SUM(Ton),0) AS Malla100,
                     SUM(Ton*PONDClayBG10)/NULLIF(SUM(Ton),0) AS Clay_Beta
                     FROM inventar_SpcHidr.resumen_mina
                     WHERE CAST(Fecha AS date) BETWEEN '2026-09-19' AND '2026-09-21'
                     GROUP BY CAST(Fecha AS date),
                       CASE WHEN Turno='TA' THEN 'A' WHEN Turno='TB' THEN 'B' ELSE Turno END
                     ORDER BY Fecha, Turno""",
            "imp": """SELECT Fecha,Turno,Ton,CuT,CuS,CuFe,CO3,Malla100,Clay_Beta,Caolinita
                       FROM DEV_SIIR.hidro.v_imp_conciliacion_chancado
                       WHERE Fecha BETWEEN '2026-09-19' AND '2026-09-21' ORDER BY Fecha,Turno""",
            "decision": """SELECT Fecha,Turno,Ton,CuT,CuS,CuFe,CO3,Malla100,Clay_Beta,Caolinita,
                       Fuente_Dato FROM inventar_SpcHidr.v_conciliacion_chancado_v2
                       WHERE Fecha BETWEEN '2026-09-19' AND '2026-09-21' ORDER BY Fecha,Turno""",
            "validated": """SELECT * FROM inventar_SpcHidr.v_leyes_validadas_tm_turno
                           WHERE Fecha BETWEEN '2026-09-19' AND '2026-09-21' ORDER BY Fecha,Turno,TM""",
            "resolved": """SELECT * FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test
                          WHERE Fecha BETWEEN '2026-09-19' AND '2026-09-21' ORDER BY Fecha,Turno,TM""",
            "generator": """SELECT * FROM inventar_SpcHidr.fn_generador_reporte_diario_emision_test(
                           '2026-09-19','2026-09-22') ORDER BY Fecha""",
            "cache": """SELECT * FROM inventar_SpcHidr.reporte_turno_cache_emision_test
                       WHERE Fecha BETWEEN '2026-09-19' AND '2026-09-21' ORDER BY Fecha,Turno""",
            "trace": """SELECT * FROM inventar_SpcHidr.trazabilidad_analitos_tm_emision_test
                       WHERE Fecha BETWEEN '2026-09-19' AND '2026-09-21' ORDER BY Fecha,Turno""",
            "definitions": """SELECT SCHEMA_NAME(o.schema_id) AS schema_name,o.name,
                       m.definition FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id
                       WHERE o.name IN ('v_conciliacion_chancado_v2','v_validacion_leyes_tm1_v2',
                       'v_validacion_leyes_tm2_v2','v_leyes_validadas_tm_turno',
                       'v_leyes_resueltas_data_tm_reporte_test','sp_reporte_turno_emision_test',
                       'sp_actualizar_reporte_turno_cache_emision_test',
                       'fn_generador_reporte_diario_emision_test','resumen_mina')""",
        }
        result = {"identity": identity, "queries": queries, "results": {}, "errors": {}}
        for name, sql in queries.items():
            try:
                data = rows(sql)
                if name == "definitions":
                    data = [{"schema_name": item["schema_name"], "name": item["name"],
                             "sha256": hashlib.sha256(item["definition"].encode()).hexdigest(),
                             "definition": item["definition"]} for item in data]
                result["results"][name] = data
            except Exception as exc:
                result["errors"][name] = str(exc)
        (HERE / "snapshot.json").write_text(
            json.dumps(result, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
        print(json.dumps({"identity": identity, "counts": {k: len(v) for k,v in result["results"].items()},
                          "errors": result["errors"]}, ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    main()

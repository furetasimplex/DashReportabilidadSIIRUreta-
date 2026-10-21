"""Preflight Fase 2A: solo SELECT; guarda evidencia local, nunca modifica SQL."""
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev, _assert_dev_connection


def main():
    destino = Path("auditorias/archivo/docs/diagnosticos/factor_camiones_fase2a") / datetime.now().strftime("%Y%m%d_%H%M%S")
    nombres = (
        "sp_mantiene_factor_ajuste_camiones_test", "Control_Factor_Ajuste_Camiones",
        "sp_mantiene_factor_ajuste_camiones_v2_test", "Control_Factor_Ajuste_Camiones_v2_test",
        "sp_factor_ajuste_camiones_test", "v_ajuste_camiones_emision_test",
    )
    with _engine_dev().connect() as conn:
        _assert_dev_connection(conn)
        identidad = dict(conn.execute(text("SELECT DB_NAME() base, CAST(SERVERPROPERTY('ServerName') AS nvarchar(128)) servidor")).mappings().one())
        destino.mkdir(parents=True, exist_ok=False)
        evidencia = {"identidad_dev_validada": identidad, "objetos": {}}
        for nombre in nombres:
            completo = "inventar_SpcHidr." + nombre
            definicion = conn.execute(text("SELECT OBJECT_DEFINITION(OBJECT_ID(:n))"), {"n": completo}).scalar()
            if definicion:
                (destino / (nombre + ".sql")).write_text(definicion, encoding="utf-8")
            columnas = [dict(r) for r in conn.execute(text("""SELECT c.name, TYPE_NAME(c.user_type_id) tipo,
                c.max_length, c.precision, c.scale, c.is_nullable
                FROM sys.columns c WHERE c.object_id=OBJECT_ID(:n) ORDER BY c.column_id"""), {"n": completo}).mappings()]
            deps = [dict(r) for r in conn.execute(text("""SELECT OBJECT_SCHEMA_NAME(referencing_id) esquema,
                OBJECT_NAME(referencing_id) consumidor, referenced_schema_name, referenced_entity_name
                FROM sys.sql_expression_dependencies
                WHERE referencing_id=OBJECT_ID(:n) OR referenced_id=OBJECT_ID(:n)"""), {"n": completo}).mappings()]
            evidencia["objetos"][nombre] = {"columnas": columnas, "dependencias": deps}
            if columnas and nombre.startswith("Control_"):
                # Nombres exclusivamente de la lista fija anterior.
                filas = [dict(r) for r in conn.execute(text("SELECT * FROM " + completo + " ORDER BY Fecha")).mappings()]
                (destino / (nombre + ".json")).write_text(json.dumps(filas, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
                evidencia["objetos"][nombre]["filas"] = len(filas)
                evidencia["objetos"][nombre]["fecha_min"] = str(filas[0]["Fecha"]) if filas else None
                evidencia["objetos"][nombre]["fecha_max"] = str(filas[-1]["Fecha"]) if filas else None
        (destino / "inspeccion.json").write_text(json.dumps(evidencia, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    print("DEV validado. Evidencia:", destino)
    for nombre, info in evidencia["objetos"].items():
        print(nombre, "filas", info.get("filas"), "desde", info.get("fecha_min"), "hasta", info.get("fecha_max"))


if __name__ == "__main__":
    main()

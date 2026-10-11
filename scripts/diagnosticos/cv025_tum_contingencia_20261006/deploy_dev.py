"""Compile or apply CV025-only DEV DDL, then reprocess 06–11 twice atomically."""
import hashlib
import json
import os
import re
import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine

HERE = Path(__file__).resolve().parent
DDL = (HERE / "ddl_deploy.sql").read_text(encoding="utf-8")
BATCHES = [x.strip() for x in re.split(r"(?im)^\s*GO\s*$", DDL) if x.strip()]
if len(BATCHES) != 5:
    raise RuntimeError("Unexpected DDL batch count")
if os.getenv("SQLSERVER_DB", "").lower() != "inventar_spchidr":
    raise RuntimeError("DEV only")

SQL = {
    "cv25": """SELECT fecha,tmh_cv025tot,tmh_cv025_tot,tmh_dia,humedad_pct,tms_dia,
        horas_con_dato_r1,horas_con_dato_r2,tag_utilizado,fuente,metodo,flag,observacion
        FROM reclamo.cv25_diario WHERE fecha BETWEEN '2026-09-01' AND '2026-09-15' ORDER BY fecha""",
    "graph": """SELECT fecha,tms_cv25,tms_topografia,tms_preliminar,diferencia_pct,flag_diferencia
        FROM reclamo.v_diferencia_cv25 WHERE fecha BETWEEN '2026-09-01' AND '2026-09-15' ORDER BY fecha""",
    "hours": """SELECT fecha_turno,turno,rotopala_id,muestras_sobre_umbral,horas_por_muestra,horas_operacion,flag
        FROM reclamo.rotopala_horas_turno WHERE fecha_turno BETWEEN '2026-09-01' AND '2026-09-15'
        ORDER BY fecha_turno,turno,rotopala_id""",
    "other_equipment": """SELECT fecha_operacional,turno,equipo_codigo,valor_final_resuelto,fuente_resuelta
        FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno
        WHERE equipo_codigo IN ('CHANCADOR_CV006','PRINCIPAL_CV008','PRINCIPAL_CV108',
              'SRR_CV001','SRR_CV002','SRR_CV003')
          AND fecha_operacional BETWEEN '2026-09-01' AND '2026-09-15'
        ORDER BY equipo_codigo,fecha_operacional,turno""",
    "episode": """SELECT fecha,pi_diario_original,tum_diario,episodio_id,estado_episodio,
        masa_pi_episodio,masa_tum_episodio,residual_masa,fuente_resuelta_dia,tmh_resuelto
        FROM inventar_SpcHidr.v_contingencia_cv025_diario_resuelto
        WHERE fecha BETWEEN '2026-09-01' AND '2026-09-15' ORDER BY fecha""",
}

def read(conn, key):
    return [dict(r) for r in conn.execute(text(SQL[key])).mappings()]

def stable_hash(rows):
    return hashlib.sha256(json.dumps(rows, default=str, sort_keys=True).encode()).hexdigest()

def check(before, first, second):
    if first["cv25"] != second["cv25"]:
        raise RuntimeError("CV25 not idempotent in business columns")
    if before["hours"] != first["hours"] or first["hours"] != second["hours"]:
        raise RuntimeError("Hours changed")
    if before["other_equipment"] != second["other_equipment"]:
        raise RuntimeError("Other equipment changed")
    top_before = {str(x["fecha"]):x["tms_topografia"] for x in before["graph"]}
    top_after = {str(x["fecha"]):x["tms_topografia"] for x in second["graph"]}
    if top_before != top_after:
        raise RuntimeError("Topography changed")
    old = {str(x["fecha"]):x for x in before["cv25"]}
    new = {str(x["fecha"]):x for x in second["cv25"]}
    wanted = {"2026-09-06":0,"2026-09-07":31387,"2026-09-08":4616,
              "2026-09-09":0,"2026-09-10":41234,"2026-09-11":63252}
    for day, target in wanted.items():
        if Decimal(str(new[day]["tmh_dia"])) != target or Decimal(str(new[day]["tms_dia"])) != target:
            raise RuntimeError(f"Unexpected resolved CV25 {day}")
        if old[day]["tmh_cv025tot"] != new[day]["tmh_cv025tot"]:
            raise RuntimeError(f"Raw PI changed {day}")
    for day in new:
        if day <= "2026-09-05" or day >= "2026-09-12":
            if old[day] != new[day]:
                raise RuntimeError(f"Normal day changed {day}")
    if sum(Decimal(str(new[day]["tms_dia"])) for day in wanted if day != "2026-09-06") != Decimal(140489):
        raise RuntimeError("Mass balance failed")
    for row in second["episode"]:
        if row["episodio_id"] == "CV025_20260907":
            if row["estado_episodio"] != "CONTINGENCIA_TUM_RECONCILIADA" or row["residual_masa"] != 0:
                raise RuntimeError("Episode did not reconcile")
    return True

def main(mode):
    with get_engine().connect() as conn:
        trans = conn.begin()
        try:
            identity = dict(conn.execute(text("SELECT @@SERVERNAME server_name,DB_NAME() database_name")).mappings().one())
            if identity["database_name"].lower() != "inventar_spchidr":
                raise RuntimeError("Wrong database")
            before = {k:read(conn,k) for k in ("cv25","graph","hours","other_equipment")}
            for i, batch in enumerate(BATCHES,1):
                conn.exec_driver_sql(batch).close()
                print("compiled",i,flush=True)
            if mode == "dry-run":
                trans.rollback()
                print("DDL compiled and rolled back")
                return
            first = None
            for n in (1,2):
                conn.execute(text("""EXEC reclamo.sp_cargar_cv25_horas
                    @FechaInicio='2026-09-06',@FechaFin='2026-09-11',
                    @HumedadPct=NULL,@TagOficial='cv025tot'""")).close()
                state = {k:read(conn,k) for k in SQL}
                if n == 1:
                    first = state
                else:
                    second = state
                print("reprocessed",n,flush=True)
            check(before,first,second)
            result = {"identity":identity,"before":before,"first":first,"second":second,
                      "hashes":{k:{"before":stable_hash(before[k]),
                                    "first":stable_hash(first[k]),"second":stable_hash(second[k])}
                                for k in before},"validation":"PASS"}
            trans.commit()
            (HERE / "post_deploy_validation.json").write_text(json.dumps(result, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
            (HERE / "idempotencia.json").write_text(json.dumps({"same_business_rows":first["cv25"]==second["cv25"],
                 "same_hours":first["hours"]==second["hours"],"same_other_equipment":first["other_equipment"]==second["other_equipment"],
                 "hash_first":stable_hash(first["cv25"]),"hash_second":stable_hash(second["cv25"])},indent=2), encoding="utf-8")
            print("PASS committed DEV transaction")
        except Exception:
            trans.rollback()
            raise

if __name__ == "__main__":
    main(sys.argv[1])

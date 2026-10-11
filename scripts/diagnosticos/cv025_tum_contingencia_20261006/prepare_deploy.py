"""Build DEV DDL and rollback from captured LIVE definitions. No DB access."""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ev = json.loads((HERE / "live_before.json").read_text(encoding="utf-8"))
defs = {x["name"]: x["definition"] for x in ev["objects"]}

def normalize(s):
    return s.replace("\r\r\n", "\n").replace("\r\n", "\n").replace("\r", "\n")

view_body = (HERE / "cv025_view_select.sql").read_text(encoding="utf-8").strip()
view_ddl = "CREATE VIEW [inventar_SpcHidr].[v_contingencia_cv025_diario_resuelto]\nAS\n" + view_body + ";"
old_sp = normalize(defs["sp_cargar_cv25_horas"])
start = old_sp.index("    /* ---- 3.a")
end = old_sp.index("    PRINT 'CV25 diario cargado", start)
header = old_sp[:start].replace("CREATE PROCEDURE", "ALTER PROCEDURE", 1)
tail = old_sp[end:]
merge = """    /* ---- 3.a  PI crudo + CV025 resuelto por episodio ------------------- */
    MERGE [reclamo].[cv25_diario] AS tgt
    USING
    (
        SELECT r.fecha,
               r.pi_diario_original AS tmh_cv025tot,
               r.pi_alternativo AS tmh_cv025_tot,
               CAST(v.rc_001 AS int) AS horas_con_dato_r1,
               CAST(v.rc_002 AS int) AS horas_con_dato_r2,
               CASE WHEN @TagOficial='cv025tot' THEN r.tmh_resuelto
                    ELSE r.pi_alternativo END AS tmh_final_elegido,
               CASE WHEN @TagOficial='cv025tot' THEN r.fuente_resuelta_dia
                    ELSE 'PI' END AS fuente_resuelta_dia,
               CASE WHEN @TagOficial='cv025tot' THEN r.estado_episodio
                    ELSE 'NORMAL_PI' END AS estado_episodio,
               r.episodio_id,r.fecha_inicio_episodio,r.fecha_recuperacion,
               r.residual_masa,r.motivo_resolucion,
               r.tum_batch_id_a,r.tum_batch_id_b
        FROM [inventar_SpcHidr].[v_contingencia_cv025_diario_resuelto] AS r
        LEFT JOIN [inventar_SpcHidr].[vista_resumen_datos_filtrados] AS v
          ON CAST(v.fecha_turno AS date)=r.fecha
        WHERE r.fecha BETWEEN @FechaInicio AND @FechaFin
    ) AS src ON tgt.fecha=src.fecha
    WHEN MATCHED THEN UPDATE SET
        tmh_cv025tot=src.tmh_cv025tot,
        tmh_cv025_tot=src.tmh_cv025_tot,
        horas_con_dato_r1=src.horas_con_dato_r1,
        horas_con_dato_r2=src.horas_con_dato_r2,
        tag_utilizado=CASE WHEN src.fuente_resuelta_dia IN ('TUM','TUM_PROVISIONAL')
                           THEN 'TUM_CV025'
                           WHEN src.fuente_resuelta_dia='SIN_RESOLVER' THEN 'SIN_RESOLVER'
                           ELSE @TagOficial END,
        tmh_dia=CASE WHEN src.tmh_final_elegido<0 THEN NULL ELSE src.tmh_final_elegido END,
        humedad_pct=COALESCE(@HumedadPct,tgt.humedad_pct),
        tms_dia=CASE WHEN src.tmh_final_elegido<0 THEN NULL
                     WHEN COALESCE(@HumedadPct,tgt.humedad_pct) IS NULL THEN src.tmh_final_elegido
                     ELSE src.tmh_final_elegido*(1.0-COALESCE(@HumedadPct,tgt.humedad_pct)/100.0) END,
        fuente=CASE WHEN src.fuente_resuelta_dia='PI' THEN 'VISTA_RESUMEN_DATOS_FILTRADOS'
                    ELSE 'CONTINGENCIA_PI_TUM_CV025' END,
        metodo=CASE WHEN src.fuente_resuelta_dia='PI' THEN 'DELTA_TOTALIZADOR_CV25_DIARIO'
                    ELSE 'EPISODIO_CV025_PI_TUM' END,
        flag=CASE WHEN src.estado_episodio='RECUPERACION_REQUIERE_REVISION' THEN 'RECUPERACION_REVISAR'
                  WHEN src.estado_episodio='SIN_TUM_NO_RESOLUBLE' THEN 'SIN_TUM_NO_RESOLUBLE'
                  WHEN src.tmh_cv025tot IS NULL AND src.tmh_cv025_tot IS NULL
                       AND src.fuente_resuelta_dia='PI' THEN 'SIN_TOTALIZADOR'
                  WHEN src.tmh_final_elegido<0 THEN 'DELTA_NEGATIVO_REVISAR'
                  WHEN src.estado_episodio='CONTINGENCIA_TUM_ABIERTA' THEN 'CONTINGENCIA_ABIERTA'
                  WHEN COALESCE(src.tmh_cv025tot,0)=0
                       AND COALESCE(src.horas_con_dato_r1,0)+COALESCE(src.horas_con_dato_r2,0)=0
                       THEN 'SIN_OPERACION'
                  ELSE 'OK' END,
        observacion=CASE WHEN src.episodio_id IS NULL THEN NULL
                    ELSE CONCAT('episodio=',src.episodio_id,'; inicio=',CONVERT(varchar(10),src.fecha_inicio_episodio,23),
                        '; recuperacion=',CONVERT(varchar(10),src.fecha_recuperacion,23),
                        '; estado=',src.estado_episodio,'; residual=',CONVERT(varchar(50),src.residual_masa),
                        '; TUM_A=',CONVERT(varchar(20),src.tum_batch_id_a),
                        '; TUM_B=',CONVERT(varchar(20),src.tum_batch_id_b)) END,
        fecha_registro=SYSDATETIME()
    WHEN NOT MATCHED BY TARGET THEN INSERT
        (fecha,tmh_cv025tot,tmh_cv025_tot,tmh_dia,humedad_pct,tms_dia,
         horas_con_dato_r1,horas_con_dato_r2,tag_utilizado,fuente,metodo,flag,observacion)
    VALUES
        (src.fecha,src.tmh_cv025tot,src.tmh_cv025_tot,
         CASE WHEN src.tmh_final_elegido<0 THEN NULL ELSE src.tmh_final_elegido END,
         @HumedadPct,
         CASE WHEN src.tmh_final_elegido<0 THEN NULL
              WHEN @HumedadPct IS NULL THEN src.tmh_final_elegido
              ELSE src.tmh_final_elegido*(1.0-@HumedadPct/100.0) END,
         src.horas_con_dato_r1,src.horas_con_dato_r2,
         CASE WHEN src.fuente_resuelta_dia IN ('TUM','TUM_PROVISIONAL') THEN 'TUM_CV025'
              WHEN src.fuente_resuelta_dia='SIN_RESOLVER' THEN 'SIN_RESOLVER'
              ELSE @TagOficial END,
         CASE WHEN src.fuente_resuelta_dia='PI' THEN 'VISTA_RESUMEN_DATOS_FILTRADOS'
              ELSE 'CONTINGENCIA_PI_TUM_CV025' END,
         CASE WHEN src.fuente_resuelta_dia='PI' THEN 'DELTA_TOTALIZADOR_CV25_DIARIO'
              ELSE 'EPISODIO_CV025_PI_TUM' END,
         CASE WHEN src.estado_episodio='RECUPERACION_REQUIERE_REVISION' THEN 'RECUPERACION_REVISAR'
              WHEN src.estado_episodio='SIN_TUM_NO_RESOLUBLE' THEN 'SIN_TUM_NO_RESOLUBLE'
              WHEN src.tmh_cv025tot IS NULL AND src.tmh_cv025_tot IS NULL
                   AND src.fuente_resuelta_dia='PI' THEN 'SIN_TOTALIZADOR'
              WHEN src.tmh_final_elegido<0 THEN 'DELTA_NEGATIVO_REVISAR'
              WHEN src.estado_episodio='CONTINGENCIA_TUM_ABIERTA' THEN 'CONTINGENCIA_ABIERTA'
              WHEN COALESCE(src.tmh_cv025tot,0)=0
                   AND COALESCE(src.horas_con_dato_r1,0)+COALESCE(src.horas_con_dato_r2,0)=0
                   THEN 'SIN_OPERACION'
              ELSE 'OK' END,
         CASE WHEN src.episodio_id IS NULL THEN NULL
              ELSE CONCAT('episodio=',src.episodio_id,'; inicio=',CONVERT(varchar(10),src.fecha_inicio_episodio,23),
                  '; recuperacion=',CONVERT(varchar(10),src.fecha_recuperacion,23),
                  '; estado=',src.estado_episodio,'; residual=',CONVERT(varchar(50),src.residual_masa),
                  '; TUM_A=',CONVERT(varchar(20),src.tum_batch_id_a),
                  '; TUM_B=',CONVERT(varchar(20),src.tum_batch_id_b)) END);

"""
new_sp = header + merge + tail
old_cv = normalize(defs["v_cv25_diario"])
old_diff = normalize(defs["v_diferencia_cv25"])
new_cv = re.sub(r"\bCREATE\s+VIEW\b", "ALTER VIEW", old_cv, count=1, flags=re.I)
new_cv = new_cv.replace("WHEN COALESCE(cv.tms_dia, 0) = 0", "WHEN cv.tms_dia IS NULL THEN NULL\n        WHEN COALESCE(cv.tms_dia, 0) = 0", 2)
if new_cv.count("WHEN cv.tms_dia IS NULL THEN NULL") != 2:
    raise RuntimeError("CV25 null propagation replacement failed")
flag_anchor = "WHEN COALESCE(cv.tms_dia, 0) = 0"
flag_at = new_cv.rfind(flag_anchor)
if flag_at < 0:
    raise RuntimeError("CV25 preliminary flag anchor missing")
new_cv = new_cv[:flag_at] + "WHEN cv.tms_dia IS NULL THEN 'SIN_RESOLVER_CV25'\n        " + new_cv[flag_at:]
new_diff = re.sub(r"\bCREATE\s+VIEW\b", "ALTER VIEW", old_diff, count=1, flags=re.I)
new_diff = new_diff.replace("WHEN COALESCE(t.modulos_topografia,0) = 0",
                            "WHEN cv.tms_dia IS NULL THEN 'SIN_RESOLVER_CV25'\n        WHEN COALESCE(t.modulos_topografia,0) = 0", 1)

def batches(items):
    return "\nGO\n\n".join(x.strip().rstrip(";") + ";" for x in items) + "\n"

constraint_ddl = """ALTER TABLE [reclamo].[cv25_diario] DROP CONSTRAINT [CK_cv_tag];
ALTER TABLE [reclamo].[cv25_diario] WITH CHECK ADD CONSTRAINT [CK_cv_tag]
CHECK ([tag_utilizado] IN ('cv025tot','cv025_tot','TUM_CV025','SIN_RESOLVER'))"""
(HERE / "ddl_deploy.sql").write_text(batches([view_ddl,constraint_ddl,new_sp,new_cv,new_diff]), encoding="utf-8")
rollback_sp = re.sub(r"\bCREATE\s+PROCEDURE\b", "ALTER PROCEDURE", old_sp, count=1, flags=re.I)
rollback_cv = re.sub(r"\bCREATE\s+VIEW\b", "ALTER VIEW", old_cv, count=1, flags=re.I)
rollback_diff = re.sub(r"\bCREATE\s+VIEW\b", "ALTER VIEW", old_diff, count=1, flags=re.I)
rollback_data = """UPDATE [reclamo].[cv25_diario]
SET tmh_dia=CASE WHEN tmh_cv025tot<0 THEN NULL ELSE tmh_cv025tot END,
    tms_dia=CASE WHEN tmh_cv025tot<0 THEN NULL WHEN humedad_pct IS NULL THEN tmh_cv025tot
                 ELSE tmh_cv025tot*(1.0-humedad_pct/100.0) END,
    tag_utilizado='cv025tot',fuente='VISTA_RESUMEN_DATOS_FILTRADOS',
    metodo='DELTA_TOTALIZADOR_CV25_DIARIO',observacion=NULL,
    flag=CASE WHEN tmh_cv025tot IS NULL AND tmh_cv025_tot IS NULL THEN 'SIN_TOTALIZADOR'
              WHEN tmh_cv025tot<0 THEN 'DELTA_NEGATIVO_REVISAR'
              WHEN COALESCE(tmh_cv025tot,0)=0
                   AND COALESCE(horas_con_dato_r1,0)+COALESCE(horas_con_dato_r2,0)=0
                   THEN 'SIN_OPERACION' ELSE 'OK' END
WHERE tag_utilizado IN ('TUM_CV025','SIN_RESOLVER')"""
restore_constraint = """ALTER TABLE [reclamo].[cv25_diario] DROP CONSTRAINT [CK_cv_tag];
ALTER TABLE [reclamo].[cv25_diario] WITH CHECK ADD CONSTRAINT [CK_cv_tag]
CHECK ([tag_utilizado]='cv025_tot' OR [tag_utilizado]='cv025tot')"""
(HERE / "rollback_cv025_contingencia.sql").write_text(
    batches([rollback_sp,rollback_cv,rollback_diff,rollback_data,restore_constraint,
             "DROP VIEW [inventar_SpcHidr].[v_contingencia_cv025_diario_resuelto]"]), encoding="utf-8")
print("Prepared DDL",len(view_ddl),len(new_sp),len(new_cv),len(new_diff))

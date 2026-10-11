#!/usr/bin/env python3
"""
test_puente_solver_nuevo.py
==============================
Investiga como construir el puente: recon_caso_oficial (solver nuevo, la
tabla "oficial" segun Luis) -> targets equivalentes a los que hoy vienen
de Data_balance_rec / rep_prod_targets, para poder correr el motor de
ajuste (rep_prod_reglas) sobre un caso del solver nuevo.

Para un caso_id de recon_caso ya oficializado (con solver_run_id), revisa:
1) recon_caso_oficial: caso_id + solver_run_id
2) recon_resultado_flujo: columnas y contenido para ese caso_id + run_id
   (necesitamos ver como se identifica cada flujo: codigo_flujo? flujo_modelo_id?)
3) recon_flujo_modelo (diccionario de flujos): como se llama/identifica cada
   flujo (para poder mapear F3=Chancado, F08/F09=SRR, F10/F11=Sal, F14/F15=
   Apilado, igual que hace hoy sp_rep_build_targets_caso con Data_balance_rec.Flujo)

Ejecutar: .venv/bin/python test_puente_solver_nuevo.py
"""
from db_connection import get_engine
import pandas as pd
pd.set_option('display.width', 220)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', 80)

engine = get_engine()

print("=" * 90)
print("1) Casos oficializados en recon_caso_oficial (candidatos para probar el puente)")
print("=" * 90)
try:
    q = """
    SELECT rco.caso_id, rc.nombre_caso, rc.fecha_inicio, rc.fecha_fin, rco.solver_run_id, rco.oficializado_en
    FROM [DEV_SIIR].[hidro].[recon_caso_oficial] rco
    INNER JOIN [DEV_SIIR].[hidro].[recon_caso] rc ON rc.id = rco.caso_id
    ORDER BY rco.oficializado_en DESC
    """
    df = pd.read_sql(q, engine)
    print(df.to_string(index=False))
except Exception as e:
    print(f"ERROR: {e}")
    df = pd.DataFrame()

if df.empty:
    print("Sin casos oficializados, no se puede continuar.")
else:
    caso_id = int(df.iloc[0]['caso_id'])
    run_id = int(df.iloc[0]['solver_run_id'])
    print(f"\nUsando caso_id={caso_id}, solver_run_id={run_id} para el resto del test")

    print(f"\n{'='*90}\n2) recon_resultado_flujo para caso_id={caso_id}, run_id={run_id}\n{'='*90}")
    try:
        q = f"""
        SELECT *
        FROM [DEV_SIIR].[hidro].[recon_resultado_flujo]
        WHERE caso_id = {caso_id} AND run_id = {run_id}
        ORDER BY 1
        """
        df2 = pd.read_sql(q, engine)
        print(f"Filas: {len(df2)}")
        print(df2.to_string(index=False))
    except Exception as e:
        print(f"ERROR: {e}")

    print(f"\n{'='*90}\n3) recon_flujo_modelo (diccionario de flujos) - columnas y muestra\n{'='*90}")
    try:
        qcols = """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM [DEV_SIIR].INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'recon_flujo_modelo'
        ORDER BY ORDINAL_POSITION
        """
        dfc = pd.read_sql(qcols, engine)
        print(dfc.to_string(index=False))
        df3 = pd.read_sql("SELECT TOP 30 * FROM [DEV_SIIR].[hidro].[recon_flujo_modelo] ORDER BY 1", engine)
        print(df3.to_string(index=False))
    except Exception as e:
        print(f"ERROR: {e}")

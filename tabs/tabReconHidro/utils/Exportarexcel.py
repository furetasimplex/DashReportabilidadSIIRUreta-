# services/export_excel.py
import pandas as pd
import openpyxl as ox
from pathlib import Path
from db_connection import get_connection  # mismo que usa utils_dash.py



def exportar_excel_desbalance(caso_id:int, plantilla:str, salida:str)->str:
    cnx = get_connection()
    SQL = f"""
    SELECT 
        Codigo AS codigo_flujo,
        Masa_medida AS ton_med,
        Ley_medida_Cu AS ley_med,
        Masa_recon AS ton_rec,
        Ley_recon_Cu AS ley_rec
    FROM inventar_SpcHidr.Data_balance_rec
    WHERE caso_id = {caso_id};
    """
    df = pd.read_sql(SQL, cnx)#, params={"caso_id": caso_id})
    cnx.close()

    wb = ox.load_workbook(plantilla, data_only=False)
    ws_b = wb["Datos bases"]           # medidos -> F (6), G (7)
    ws_r = wb["Datos Reconciliados"]   # reconc -> J (10), K (11)

    idx_b, idx_r = {}, {}
    for row in range(6, ws_b.max_row+1):
        code = ws_b.cell(row=row, column=2).value  # B: codigo_flujo
        if not code: break
        idx_b[str(code).strip()] = row
    for row in range(3, ws_r.max_row+1):
        code = ws_r.cell(row=row, column=2).value  # B: codigo_flujo
        if not code: break
        idx_r[str(code).strip()] = row

    for _, r in df.iterrows():
        c = str(r["codigo_flujo"]).strip()
        # Medidos
        if c in idx_b:
            rr = idx_b[c]
            if pd.notna(r["ton_med"]): ws_b.cell(row=rr, column=6,  value=float(r["ton_med"]))
            if pd.notna(r["ley_med"]): ws_b.cell(row=rr, column=7,  value=float(r["ley_med"]))
        # Reconciliados
        if c in idx_r:
            rr = idx_r[c]
            if pd.notna(r["ton_rec"]): ws_r.cell(row=rr, column=10, value=float(r["ton_rec"]))
            if pd.notna(r["ley_rec"]): ws_r.cell(row=rr, column=11, value=float(r["ley_rec"]))

    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    wb.save(salida)
    return salida

import base64
import io
import os
import pandas as pd
import plotly.express as px
import numpy as np
import string
import sqlalchemy
#from databricks import sql
#import mariadb
import sys
import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
#import mysql.connector
import os
from dotenv import load_dotenv
from dash import Dash
from db_connection import get_connection, get_engine
from datetime import date
import math
import traceback
import pyodbc

load_dotenv()

app = Dash(__name__, suppress_callback_exceptions=True)



def get_data_agua_casos(inicio, final, crea_caso):
    """
    VERSIÓN DE DEPURACIÓN: No cambiar la lógica, solo añadir prints para diagnóstico.
    """
    print("\n" + "="*50)
    print("--- INICIANDO get_data_agua_casos ---")
    print(f"--- PARÁMETROS RECIBIDOS: inicio='{inicio}', final='{final}', crea_caso='{crea_caso}'")
    
    db = get_connection()
    cursor = db.cursor()
    ddf_casos = pd.DataFrame()
    
    try:
        if crea_caso == "Si":
            # --- RUTA DE CREACIÓN ---
            print("--- LÓGICA: Entrando en la ruta de CREACIÓN de caso.")
            nombre_default = f"Reconciliación {inicio} a {final}"
            
            sql_insert = f"""
                INSERT INTO inventar_SpcHidr.casos_balance (fecha, modelo, fecha_ini, nombre_caso)
                VALUES ('{final}', 1, '{inicio}', '{nombre_default}');
            """
            print(f"--- DEBUG: Ejecutando SQL INSERT:\n{sql_insert}")
            cursor.execute(sql_insert)
            print("--- DEBUG: INSERT ejecutado. Solicitando SCOPE_IDENTITY()...")

            cursor.execute("SELECT SCOPE_IDENTITY();")
            result = cursor.fetchone()
            print(f"--- DEBUG: Resultado de SCOPE_IDENTITY(): {result}")

            if result is None or result[0] is None:
                db.commit() # Intentamos confirmar por si acaso, aunque es anómalo
                print("--- ERROR CRÍTICO: SCOPE_IDENTITY() no devolvió un ID. El INSERT pudo haber fallado silenciosamente.")
                # Devolvemos un DF vacío porque no podemos continuar.
                db.close()
                return pd.DataFrame()

            new_case_id = result[0]
            print(f"--- DEBUG: Nuevo ID de caso obtenido: {new_case_id}. Realizando COMMIT...")
            db.commit()
            print("--- DEBUG: COMMIT realizado con éxito.")

            sql_select = f"""
                SELECT caso_id, fecha, comentarios, modelo, fecha_ini, nombre_caso
                FROM inventar_SpcHidr.casos_balance
                WHERE caso_id = {new_case_id};
            """
            print(f"--- DEBUG: Ejecutando SQL SELECT para el nuevo caso:\n{sql_select}")
            
        else:
            # --- RUTA DE BÚSQUEDA ---
            print("--- LÓGICA: Entrando en la ruta de BÚSQUEDA de caso.")
            sql_select = f"""
                SELECT TOP 1 caso_id, fecha, comentarios, modelo, fecha_ini, nombre_caso
                FROM inventar_SpcHidr.casos_balance
                WHERE modelo = 1 AND fecha_ini = '{inicio}' AND fecha = '{final}'
                ORDER BY caso_id DESC;
            """
            print(f"--- DEBUG: Ejecutando SQL SELECT para buscar caso existente:\n{sql_select}")

        ddf_casos = pd.read_sql(sql_select, db)
        print("--- DEBUG: DataFrame resultante de la consulta SELECT:")
        print(ddf_casos)

    except Exception as e:
        print("--- ERROR FATAL en get_data_agua_casos ---")
        traceback.print_exc()
        ddf_casos = pd.DataFrame()
    finally:
        print("--- CERRANDO CONEXIÓN A LA BASE DE DATOS ---")
        print("="*50 + "\n")
        db.close()

    return ddf_casos

def get_agua_his_casos (final):
    ddf_casos = pd.DataFrame()  # 👈 evita devolver None
    db=get_connection()
    sql2 = ("SELECT caso_id, fecha, comentarios, modelo, fecha_ini, nombre_caso FROM inventar_SpcHidr.casos_balance WHERE modelo = 1 ORDER BY fecha DESC")
    print(sql2)
    cursor = db.cursor()
    print("🟢 Cursor creado correctamente")
    try:
        cursor.execute(sql2)
        registros = [list(r) for r in cursor.fetchall()]  # convierte cada tupla en lista plana
        column_names = [desc[0] for desc in cursor.description]
                
        ddf_casosh = pd.DataFrame(registros, columns=column_names)
        #ddf_casos = pd.DataFrame(registros)
        print(ddf_casosh)
        #ddf_casos.rename(columns={0:'Id_caso', 1:'fecha', 2:'observaciones', 3:'modelo', 4:'fecha_ini', 5:'nombre_caso' }, inplace=True)
        #ddf_casos.rename(columns={'Id_caso', 'fecha', 'comentarios', 'modelo', 'fecha_ini', 'nombre_caso' }, inplace=True)
        #print(ddf_casos)
    except Exception as e:
        print("Error en la consulta",e)
    finally:
            cursor.close()
    return ddf_casosh

def get_fig_bal_casos(maxid, agg_tab2):
    print("📁 Ruta actual:", os.getcwd())
    
    image_path = "assets/diagrama ripios3.png"
    if not os.path.exists(image_path):
        print(f"❌ Imagen no encontrada: {image_path}")
        return ""
    
    # ... (El código para cargar y procesar la imagen con cv2 es correcto y no cambia) ...
    image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if image is None: return ""
    if image.shape[2] == 4:
        b, g, r, a = cv2.split(image)
        mask = a[:, :, None]
        blanco = np.ones_like(image[:, :, :3]) * 255
        image = np.where(mask == 0, blanco, image[:, :, :3])
    
    db = get_connection()
    # --- CAMBIO IMPORTANTE AQUÍ ---
    # La consulta ahora usa un marcador de posición '?'
    data_sql = """
        SELECT ID, id_flujo, Etiqueta, Descripcion, fecha, X, Y, X_l, Y_l, modelo, 
               Medido, Reconciliado, Medido_cu, Reconciliado_cu, Tolerancia, 
               Tolerancia_cu, caso
        FROM inventar_SpcHidr.flujo_caso_coord
        WHERE caso = ? 
    """
    df = pd.DataFrame() # DataFrame vacío por defecto
    try:
        # Pasamos el valor de 'maxid' de forma segura como un parámetro
        df = pd.read_sql(data_sql, db, params=(maxid,))
    except Exception as e:
        print("Error en la consulta de coordenadas:", e)
    finally:
        db.close()

    alto, ancho = image.shape[:2]
    dpi = 100
    figsize = (ancho / dpi, alto / dpi)
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    if not df.empty:
        if agg_tab2 == "Reconciliado":
            for _, row in df.iterrows():
                ax.text(row["X"], row["Y"], f"{row['Reconciliado']:.0f}", color="black", fontsize=9, weight="bold")
                ax.text(row["X_l"], row["Y_l"], f"{row['Reconciliado_cu']:.2f}", color="black", fontsize=9, weight="bold")
        elif agg_tab2 == "Medido":
            for _, row in df.iterrows():
                ax.text(row["X"], row["Y"], f"{row['Medido']:.0f}", color="black", fontsize=9, weight="bold")
                ax.text(row["X_l"], row["Y_l"], f"{row['Medido_cu']:.2f}", color="black", fontsize=9, weight="bold")
        else:
            for _, row in df.iterrows():
                ax.text(row["X"], row["Y"], f"{row['Tolerancia']:.0f}", color="black", fontsize=9, weight="bold")
                ax.text(row["X_l"], row["Y_l"], f"{row['Tolerancia_cu']:.2f}", color="black", fontsize=9, weight="bold")
    
    ax.axis("off")
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close(fig)

    return f"data:image/png;base64,{img_base64}"

def get_data_save_casos(dat_casos, final, maxcas):
    if not dat_casos:
        return

    row_data = dat_casos[0]
    cols_to_update = [col for col in row_data.keys() if col != "caso_id"]
    set_clause = ", ".join([f"[{col}] = ?" for col in cols_to_update])
    
    values = [_to_native(row_data[col]) for col in cols_to_update]
    values.append(int(maxcas))

    query = f"UPDATE inventar_SpcHidr.casos_balance SET {set_clause} WHERE caso_id = ?;"
    
    db = get_connection()
    cursor = db.cursor()
    try:
        cursor.execute(query, tuple(values))
        db.commit()
    except Exception as e:
        db.rollback()
        print("❌ Error en la actualización del caso:", e)
    finally:
        cursor.close()
        db.close()

def calcular_desbalance_nodo_desde_reconciliado(engine, df_rec):
    """
    Calcula desbalances por nodo usando datos reconciliados
    (reutilizable para grabación y reportabilidad)
    """
    topo = pd.read_sql(
        """
        SELECT Id_flujo, n_salida, n_llegada
        FROM inventar_SpcHidr.flujo_modelos
        WHERE activo = 1
        """,
        engine
    )

    df = df_rec.merge(
        topo,
        left_on="id_flujo",
        right_on="Id_flujo",
        how="inner"
    )

    if df.empty:
        return pd.DataFrame()

    rows = []
    nodos = pd.unique(df[["n_salida", "n_llegada"]].values.ravel())

    for nodo in nodos:
        ent = df[df["n_llegada"] == nodo]
        sal = df[df["n_salida"] == nodo]

        masa_in  = ent["Masa_recon"].sum()
        masa_out = sal["Masa_recon"].sum()

        fino_in  = (ent["Masa_recon"] * ent["Ley_recon_Cu"] / 100).sum()
        fino_out = (sal["Masa_recon"] * sal["Ley_recon_Cu"] / 100).sum()

        rows.append({
            "codigo_nodo": nodo,
            "masa_entrada": masa_in,
            "masa_salida": masa_out,
            "desb_masa_abs": masa_in - masa_out,
            "desb_masa_pct": (masa_in - masa_out) / masa_in * 100 if masa_in else None,
            "fino_entrada_cu": fino_in,
            "fino_salida_cu": fino_out,
            "desb_fino_cu_abs": fino_in - fino_out,
            "desb_fino_cu_pct": (fino_in - fino_out) / fino_in * 100 if fino_in else None,
        })

    return pd.DataFrame(rows)

# ---------- util de saneo ----------
def _to_native(v):
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, (np.floating,)):
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(v, (np.integer,)):
        return int(v)
    if pd.isna(v):
        return None
    if isinstance(v, pd.Timestamp):
        return v.date()
    return v

def _norm(s):
    if pd.isna(s):
        return None
    return str(s).strip().lower()

def get_data_publica_casos(med_cas, rec_caso, shared):
    if not rec_caso: raise ValueError("No hay datos reconciliados (rec_caso).")
    if not isinstance(shared, dict) or shared.get("caso_id") is None: raise ValueError("Falta 'caso_id' en 'shared'.")

    # --- Lógica de preparación de DataFrames (sin cambios) ---
    caso_id = int(shared["caso_id"])
    fecha_bm = pd.to_datetime(shared.get("fecha_fin", date.today())).date()
    df_rec = pd.DataFrame(rec_caso); df_med = pd.DataFrame(med_cas or [])
    rename_rec = {'Masa medida':'Masa_medida', 'Masa recon':'Masa_recon', 'Error masa':'Error_masa', 'Ley medida Cu':'Ley_medida_Cu', 'Ley recon Cu':'Ley_recon_Cu', 'Error ley Cu':'Error_ley_Cu'}
    df_rec.rename(columns=rename_rec, inplace=True)
    if 'Codigo' in df_rec.columns: df_rec['Codigo'] = df_rec['Codigo'].astype(str).str.strip()
    if 'Flujo' in df_rec.columns: df_rec['Flujo'] = df_rec['Flujo'].astype(str).str.strip()
    keep_med = ['id_flujo', 'codigo_flujo', 'nombre_flujo', 'Cu', 'FCu', 'Tolerancia', 'Tolerancia_cu']
    for k in keep_med:
        if k not in df_med.columns: df_med[k] = None
    df_med['codigo_flujo'] = df_med['codigo_flujo'].astype(str).str.strip()
    df_med['nombre_flujo'] = df_med['nombre_flujo'].astype(str).str.strip()
    df_out = df_rec.merge(df_med[keep_med], left_on='Codigo', right_on='codigo_flujo', how='left', suffixes=('', '_med'))
    mask_missing = df_out['id_flujo'].isna()
    if mask_missing.any():
        aux_rec = df_out.loc[mask_missing, ['Flujo']].copy(); aux_rec['Flujo_norm'] = aux_rec['Flujo'].map(_norm)
        aux_med = df_med[['nombre_flujo', 'id_flujo', 'Cu', 'FCu', 'Tolerancia', 'Tolerancia_cu']].copy(); aux_med['Flujo_norm'] = aux_med['nombre_flujo'].map(_norm)
        aux_join = aux_rec.merge(aux_med.drop_duplicates('Flujo_norm'), on='Flujo_norm', how='left', suffixes=('', '_nm'))
        df_out.loc[mask_missing, 'id_flujo'] = aux_join['id_flujo'].values
        for col in ['Cu', 'FCu', 'Tolerancia', 'Tolerancia_cu']:
            if col in df_out.columns and col in aux_join.columns: df_out.loc[mask_missing, col] = df_out.loc[mask_missing, col].fillna(aux_join[col].values)
    if 'Codigo' not in df_out.columns or df_out['Codigo'].isna().all():
        if 'codigo_flujo' in df_out.columns: df_out['Codigo'] = df_out['codigo_flujo']
    df_out['Masa_Medida2'] = df_out.get('Masa_medida')

    # --- CAMBIO CLAVE: REORDENAR LAS COLUMNAS PARA QUE COINCIDAN CON LA BD ---
    # Este es el orden físico de tu tabla Data_balance_rec (sin bms_id)
    cols_db_orden_real = [
        'Flujo', 'Masa_medida', 'Masa_recon', 'Ley_medida_Cu', 'Ley_recon_Cu', 'Error_ley_Cu',
        'Error_masa', 'Codigo', 'Masa_Medida2', 'Cu', 'FCu', 'Tolerancia',
        'id_flujo', 'Tolerancia_cu', 'caso_id', 'fecha_bm'
    ]
    df_out['caso_id'] = caso_id
    df_out['fecha_bm'] = fecha_bm
    for c in cols_db_orden_real:
        if c not in df_out.columns: df_out[c] = None
    df_out = df_out[cols_db_orden_real] # Forzamos el DataFrame a tener el orden correcto

    # --- Lógica de tipos y limpieza (sin cambios) ---
    num_cols_float = ['Masa_medida','Masa_recon','Ley_medida_Cu','Ley_recon_Cu','Error_ley_Cu', 'Error_masa', 'Masa_Medida2','Cu','FCu','Tolerancia']
    num_cols_int = ['id_flujo','Tolerancia_cu','caso_id']
    for c in num_cols_float: df_out[c] = pd.to_numeric(df_out[c], errors='coerce')
    for c in num_cols_int: df_out[c] = pd.to_numeric(df_out[c], errors='coerce')
    df_out['fecha_bm'] = pd.to_datetime(df_out['fecha_bm'], errors='coerce').dt.date

    rows = [tuple(_to_native(v) for v in row) for row in df_out.itertuples(index=False, name=None)]
    if not rows:
        return 0

    # --- Lógica de Base de Datos Final y Alineada ---
    cnx = get_connection()
    cur = cnx.cursor()
    try:
        cur.execute("DELETE FROM inventar_SpcHidr.Data_balance_rec WHERE caso_id = ?", (caso_id,))
        
        # El INSERT ahora tiene las columnas en el orden correcto
        insert_sql = """
            INSERT INTO inventar_SpcHidr.Data_balance_rec
            (Flujo, Masa_medida, Masa_recon, Ley_medida_Cu, Ley_recon_Cu, Error_ley_Cu,
             Error_masa, Codigo, Masa_Medida2, Cu, FCu, Tolerancia,
             id_flujo, Tolerancia_cu, caso_id, fecha_bm)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Usamos el bucle 'for' que es el método más seguro
        for row in rows:
            cur.execute(insert_sql, row)
        
        cnx.commit()

            # ==========================================================
        # NUEVO BLOQUE: DESBALANCE POR NODO
        # ==========================================================

        engine = get_engine()

        df_rec_calc = df_out.copy()

        df_desb = calcular_desbalance_nodo_desde_reconciliado(engine, df_rec_calc)

        if not df_desb.empty:
            df_desb["caso_id"] = caso_id
            df_desb["fecha_ini_periodo"] = pd.to_datetime(
                shared.get("fecha_inicio", fecha_bm)
            ).date()
            df_desb["fecha_fin_periodo"] = fecha_bm
            df_desb["fecha_registro"] = date.today()

            cnx2 = get_connection()
            cur2 = cnx2.cursor()
            try:
                # Limpieza previa del caso
                cur2.execute(
                    "DELETE FROM inventar_SpcHidr.bm_desbalance_nodo WHERE caso_id = ?",
                    (caso_id,)
                )

                insert_sql = """
                INSERT INTO inventar_SpcHidr.bm_desbalance_nodo
                (caso_id, codigo_nodo, fecha_ini_periodo, fecha_fin_periodo,
                masa_entrada, masa_salida, desb_masa_abs, desb_masa_pct,
                fino_entrada_cu, fino_salida_cu, desb_fino_cu_abs, desb_fino_cu_pct,
                fecha_registro)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

                for _, r in df_desb.iterrows():
                    cur2.execute(
                        insert_sql,
                        (
                            caso_id,
                            r["codigo_nodo"],
                            df_desb["fecha_ini_periodo"].iloc[0],
                            df_desb["fecha_fin_periodo"].iloc[0],
                            r["masa_entrada"],
                            r["masa_salida"],
                            r["desb_masa_abs"],
                            r["desb_masa_pct"],
                            r["fino_entrada_cu"],
                            r["fino_salida_cu"],
                            r["desb_fino_cu_abs"],
                            r["desb_fino_cu_pct"],
                            r["fecha_registro"],
                        )
                    )

                cnx2.commit()

            except Exception as e:
                cnx2.rollback()
                raise e
            finally:
                cur2.close()
                cnx2.close()

        return len(rows)
    except Exception as e:
        cnx.rollback()
        raise e
    finally:
        cur.close()
        cnx.close()

# ******************************************************************************     




def parse_contents(contents, filename):
    """
    Función que transforma el contenido de un archivo csv, xls o xlsx cargado
    mediante dcc.Upload().
    """
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = None
    try:
        if 'csv' in filename:
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename:
            df = pd.read_excel(io.BytesIO(decoded))
        elif 'xlsx' in filename:
            df = pd.read_excel(io.BytesIO(decoded))
    except Exception as e:
        print(e)
        return df
    return df

def local_img_to_html(path,img_name):
    """
    Función que transforma una imagen local png a string basico para ser
    desplegado layout.
    Se ingresan path y nombre del archivo, y se retorna el string en el formato
    que debe ser entregado en la propiedad src de "html.Img()"
    Ejemplo:
    html.Img( src=local_img_to_html(assets_folder,'Mi-imagen.png') )
    """
    image_filename = os.path.join(path, img_name)
    encoded_image = base64.b64encode(open(image_filename, 'rb').read()).decode("UTF-8")
    return 'data:image/png;base64,{}'.format(encoded_image)


def get_info_caso_html(maxid):
    """
    Devuelve los datos para el flowsheet D3:
    - flowData con Medido / Reconciliado / Tolerancias (TMS, Cu, Mo)
    - nodeData vacío por ahora
    """
    db = get_connection()

    sql = """
        SELECT ID, id_flujo, Etiqueta, Descripcion, fecha, X, Y, X_l, Y_l, modelo, 
               Medido, Reconciliado, Medido_cu, Reconciliado_cu, Tolerancia, 
               Tolerancia_cu, caso
        FROM inventar_SpcHidr.flujo_caso_coord
        WHERE caso = ?
    """

    df = pd.read_sql(sql, db, params=(maxid,))
    db.close()

    flowData = {}

    if not df.empty:
        for _, row in df.iterrows():
            flujo = str(row["id_flujo"]).strip()  # p.ej "F3"

            if flujo not in flowData:
                flowData[flujo] = {
                    "TMS": {  # medido
                        "Masa medida": None,
                        "Masa recon": None,
                    },
                    "Cu": {   # recon
                        "Ley medida Cu": None,
                        "Ley recon Cu": None,
                    },
                    "Mo": {   # TOLERANCIAS
                        "Ley medida Mo": None,
                        "Ley recon Mo": None,
                    }
                }

            # -----------------------------
            # MASA (TMS)
            # -----------------------------
            flowData[flujo]["TMS"]["Masa medida"] = (
                float(row["Medido"]) if row["Medido"] is not None else None
            )
            flowData[flujo]["TMS"]["Masa recon"] = (
                float(row["Reconciliado"]) if row["Reconciliado"] is not None else None
            )

            # -----------------------------
            # LEY CU
            # -----------------------------
            flowData[flujo]["Cu"]["Ley medida Cu"] = (
                float(row["Medido_cu"]) if row["Medido_cu"] is not None else None
            )
            flowData[flujo]["Cu"]["Ley recon Cu"] = (
                float(row["Reconciliado_cu"]) if row["Reconciliado_cu"] is not None else None
            )

            # -----------------------------
            # TOLERANCIAS (Mo en el flowsheet)
            # -----------------------------
            flowData[flujo]["Mo"]["Ley medida Mo"] = (
                float(row["Tolerancia"]) if row["Tolerancia"] is not None else None
            )
            flowData[flujo]["Mo"]["Ley recon Mo"] = (
                float(row["Tolerancia_cu"]) if row["Tolerancia_cu"] is not None else None
            )

    # nodeData vacío por ahora
    nodeData = {}

    return {
        "flowData": flowData,
        "nodeData": nodeData
    }

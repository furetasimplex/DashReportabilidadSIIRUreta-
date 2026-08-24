import base64
import io
import os
import pandas as pd
import plotly.express as px
import numpy as np
import string
import sqlalchemy
import sys
import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from dash import Dash
from db_connection import get_connection
from datetime import date
import math

load_dotenv()

app = Dash(__name__, suppress_callback_exceptions=True)



def get_data_agua_casos(inicio, final,crea_caso):
        db=get_connection()
        if crea_caso=="Si":
            sql_in="INSERT INTO `casos_balance` ( `fecha`,  `modelo`, `fecha_ini`) VALUES" \
            " ( '"+(final)+"',  1, '"+(inicio)+"');" 
            #print(sql_in)
            
            cursor = db.cursor()
            try:
                cursor.execute(sql_in)  
                db.commit()
            except:
                print("Error en insertar")
            

        sql="select caso_id, fecha, comentarios, modelo, fecha_ini, nombre_caso " \
        "FROM casos_balance where casos_balance.fecha='"+(final)+"' and modelo=1"
        #print(sql)
        cursor = db.cursor()
        try:
            cursor.execute(sql)
            registros = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            ddf_casos = pd.DataFrame(registros, columns=column_names)
            #ddf_casos = pd.DataFrame(registros)
            print(ddf_casos)
            #ddf_casos.rename(columns={0:'Id_caso', 1:'fecha', 2:'observaciones', 3:'modelo', 4:'fecha_ini', 5:'nombre_caso' }, inplace=True)
            #ddf_casos.rename(columns={'Id_caso', 'fecha', 'comentarios', 'modelo', 'fecha_ini', 'nombre_caso' }, inplace=True)
            #print(ddf_casos)
        except:
            print("Error en la consulta")
        finally:
                cursor.close()
        return ddf_casos

def get_agua_his_casos (final):
     db=get_connection()
     sql2="select caso_id, fecha, comentarios, modelo, fecha_ini, nombre_caso " \
        "FROM casos_balance where  modelo=1 order by fecha desc"
     print(sql2)
     cursor = db.cursor()
     try:
            cursor.execute(sql2)
            registros = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            ddf_casosh = pd.DataFrame(registros, columns=column_names)
            #ddf_casos = pd.DataFrame(registros)
            print(ddf_casosh)
            #ddf_casos.rename(columns={0:'Id_caso', 1:'fecha', 2:'observaciones', 3:'modelo', 4:'fecha_ini', 5:'nombre_caso' }, inplace=True)
            #ddf_casos.rename(columns={'Id_caso', 'fecha', 'comentarios', 'modelo', 'fecha_ini', 'nombre_caso' }, inplace=True)
            #print(ddf_casos)
     except:
            print("Error en la consulta")
     finally:
                cursor.close()
     return ddf_casosh

def get_fig_bal_casos(maxid,agg_tab2):
    print("📁 Ruta actual:", os.getcwd())
    
    image_path = "assets/diagrama ripios3.png"
    if not os.path.exists(image_path):
        print(f"❌ Imagen no encontrada: {image_path}")
        return ""
    
    image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    print("✅ Imagen encontrada.")
    
    if image is None:
        print("❌ Error al cargar la imagen (es None)")
        return ""

    if image.shape[2] == 4:
        b, g, r, a = cv2.split(image)
        mask = a[:, :, None]
        blanco = np.ones_like(image[:, :, :3]) * 255
        image = np.where(mask == 0, blanco, image[:, :, :3])
    db=get_connection()
    data_sql =     '''SELECT
                    flujo_caso_coord.ID, 
                    flujo_caso_coord.id_flujo, 
                    flujo_caso_coord.Etiqueta, 
                    flujo_caso_coord.Descripcion, 
                    flujo_caso_coord.fecha, 
                    flujo_caso_coord.X, 
                    flujo_caso_coord.Y, 
                    flujo_caso_coord.X_l, 
                    flujo_caso_coord.Y_l, 
                    flujo_caso_coord.modelo, 
                    flujo_caso_coord.Medido, 
                    flujo_caso_coord.Reconciliado, 
                    flujo_caso_coord.Medido_cu, 
                    flujo_caso_coord.Reconciliado_cu, 
                    flujo_caso_coord.Tolerancia, 
                    flujo_caso_coord.Tolerancia_cu, 
                    flujo_caso_coord.caso
                FROM
                    flujo_caso_coord
                WHERE
                    flujo_caso_coord.caso = '''+ str(maxid) 
    print(data_sql)
    cursor = db.cursor()
    try:
            cursor.execute(data_sql)
            registros = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(registros, columns=column_names)
            print(df)
    except:
            print("Error en la consulta coord")
            return ""
    finally:
                cursor.close()

    
   
    alto, ancho = image.shape[:2]
    dpi = 100  # puedes ajustar esto

    figsize = (ancho / dpi, alto / dpi)
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    #fig, ax = plt.subplots(figsize=(12, 7))
    ax.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    if agg_tab2=="Reconciliado":

        for _, row in df.iterrows():
            x, y = row["X"], row["Y"]
            value = round(row["Reconciliado"], 2)
            ax.text(x, y, f"{value:.0f}", color="black", fontsize=9, weight="bold")
            x_l, y_l = row["X_l"], row["Y_l"]
            value_l = round(row["Reconciliado_cu"], 2)
            ax.text(x_l, y_l, f"{value_l:.2f}", color="black", fontsize=9, weight="bold") 
    elif agg_tab2=="Medido":
         for _, row in df.iterrows():
            x, y = row["X"], row["Y"]
            value = round(row["Medido"], 2)
            ax.text(x, y, f"{value:.0f}", color="black", fontsize=9, weight="bold")
            x_l, y_l = row["X_l"], row["Y_l"]
            value_l = round(row["Medido_cu"], 2)
            ax.text(x_l, y_l, f"{value_l:.2f}", color="black", fontsize=9, weight="bold") 
    else:
         for _, row in df.iterrows():
            x, y = row["X"], row["Y"]
            value = round(row["Tolerancia"], 2)
            ax.text(x, y, f"{value:.0f}", color="black", fontsize=9, weight="bold")
            x_l, y_l = row["X_l"], row["Y_l"]
            value_l = round(row["Tolerancia_cu"], 2)
            ax.text(x_l, y_l, f"{value_l:.2f}", color="black", fontsize=9, weight="bold") 
         

    ax.axis("off")

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.savefig("diagrama_hidro.png")
    plt.close(fig)

    return f"data:image/png;base64,{img_base64}"

def get_data_save_casos(dat_casos,final,maxcas):
        #column_names = [desc[0] for desc in dat_casos.description]
        df = pd.DataFrame(dat_casos)
        print(df)
        # Generar sentencias UPDATE
        tabla = "casos_balance"  # Nombre de la tabla en MySQL
        update_statements = []

        for _, row in df.iterrows():
            set_values = ", ".join([f"{col} = '{row[col]}'" if isinstance(row[col], str) else f"{col} = {row[col]}" for col in df.columns if col != 'caso_id'])
            update_statements.append(f"UPDATE {tabla} SET {set_values} WHERE caso_id = {maxcas};")

        # Unir todas las sentencias en una sola cadena
        query = "\n".join(update_statements)

        # Mostrar resultado
        print(query)   
        db=get_connection()
        cursor = db.cursor()
        for q in query.strip().split(";"):
            if q.strip():
                try:
                    cursor.execute(q.strip() + ";")
                    db.commit()
                except Exception as e:
                    print("❌ Error en la sentencia:", q.strip())
                    print("🔎 Detalle:", e)     
                finally:
                    cursor.close()
        return 


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
    """
    Publica en Data_balance_rec combinando:
      - med_cas: rowData de 'recon-data-base' (editable)
      - rec_caso: rowData de 'recon-resultados' (reconciliado)
      - shared: dict con {"caso_id": int, "fecha": "YYYY-MM-DD"}
    Devuelve: número de filas insertadas.
    """
    if not rec_caso:
        raise ValueError("No hay datos reconciliados (rec_caso).")
    if not isinstance(shared, dict) or shared.get("caso_id") is None:
        raise ValueError("Falta 'caso_id' en 'shared'.")

    caso_id = int(shared["caso_id"])

    # fecha_bm desde shared['fecha'] si existe; si no, hoy
    fecha_bm = date.today()
    f = shared.get("fecha")
    if f:
        ts = pd.to_datetime(f, errors="coerce")
        if pd.notna(ts):
            fecha_bm = ts.date()

    # DataFrames
    df_rec = pd.DataFrame(rec_caso).copy()
    df_med = pd.DataFrame(med_cas or []).copy()

    # Renombrar rec → columnas de la tabla
    rename_rec = {
        'Masa medida':   'Masa_medida',
        'Masa recon':    'Masa_recon',
        'Error masa':    'Error_masa',
        'Ley medida Cu': 'Ley_medida_Cu',
        'Ley recon Cu':  'Ley_recon_Cu',
        'Error ley Cu':  'Error_ley_Cu',
    }
    df_rec.rename(columns=rename_rec, inplace=True)

    # Normaliza claves y evita espacios
    if 'Codigo' in df_rec.columns:
        df_rec['Codigo'] = df_rec['Codigo'].astype(str).str.strip()
    if 'Flujo' in df_rec.columns:
        df_rec['Flujo'] = df_rec['Flujo'].astype(str).str.strip()

    # ---- Merge por CODIGO (preferente)
    keep_med = ['id_flujo', 'codigo_flujo', 'nombre_flujo', 'Cu', 'FCu', 'Tolerancia', 'Tolerancia_cu']
    for k in keep_med:
        if k not in df_med.columns:
            df_med[k] = None
    df_med['codigo_flujo'] = df_med['codigo_flujo'].astype(str).str.strip()
    df_med['nombre_flujo'] = df_med['nombre_flujo'].astype(str).str.strip()

    df_out = df_rec.merge(
        df_med[keep_med],
        left_on='Codigo', right_on='codigo_flujo',
        how='left', suffixes=('', '_med')
    )

    # ---- Fallback: merge por nombre de flujo normalizado
    mask_missing = df_out['id_flujo'].isna()
    if mask_missing.any():
        aux_rec = df_out.loc[mask_missing, ['Flujo']].copy()
        aux_rec['Flujo_norm'] = aux_rec['Flujo'].map(_norm)

        aux_med = df_med[['nombre_flujo', 'id_flujo', 'Cu', 'FCu', 'Tolerancia', 'Tolerancia_cu']].copy()
        aux_med['Flujo_norm'] = aux_med['nombre_flujo'].map(_norm)

        aux_join = aux_rec.merge(
            aux_med.drop_duplicates('Flujo_norm'),
            on='Flujo_norm', how='left', suffixes=('', '_nm')
        )

        df_out.loc[mask_missing, 'id_flujo'] = aux_join['id_flujo'].values
        for col in ['Cu', 'FCu', 'Tolerancia', 'Tolerancia_cu']:
            if col in df_out.columns and col in aux_join.columns:
                df_out.loc[mask_missing, col] = df_out.loc[mask_missing, col].fillna(aux_join[col].values)

    # Completa 'Codigo' si viene vacío en rec
    if 'Codigo' not in df_out.columns or df_out['Codigo'].isna().all():
        if 'codigo_flujo' in df_out.columns:
            df_out['Codigo'] = df_out['codigo_flujo']

    # Otras columnas requeridas por la tabla
    df_out['Masa_Medida2'] = df_out.get('Masa_medida')
    df_out['caso_id'] = caso_id
    df_out['fecha_bm'] = fecha_bm

    # Orden final según tu DDL
    cols_db = [
        'Flujo',
        'Masa_medida', 'Masa_recon', 'Error_masa',
        'Ley_medida_Cu', 'Ley_recon_Cu', 'Error_ley_Cu',
        'id_flujo', 'Codigo',
        'Masa_Medida2',
        'Cu', 'FCu', 'Tolerancia', 'Tolerancia_cu',
        'caso_id', 'fecha_bm'
    ]
    for c in cols_db:
        if c not in df_out.columns:
            df_out[c] = None
    df_out = df_out.reindex(columns=cols_db)

    # Tipos numéricos
    num_cols_float = ['Masa_medida','Masa_recon','Error_masa','Ley_medida_Cu','Ley_recon_Cu','Error_ley_Cu',
                      'Masa_Medida2','Cu','FCu','Tolerancia']
    num_cols_int = ['id_flujo','Tolerancia_cu','caso_id']
    for c in num_cols_float:
        df_out[c] = pd.to_numeric(df_out[c], errors='coerce')
    for c in num_cols_int:
        df_out[c] = pd.to_numeric(df_out[c], errors='coerce')

    # Fecha
    df_out['fecha_bm'] = pd.to_datetime(df_out['fecha_bm'], errors='coerce').dt.date

    # Filas limpias para insert (NaN→None, tipos nativos)
    rows = [tuple(_to_native(v) for v in row) for row in df_out.itertuples(index=False, name=None)]
    if not rows:
        return 0

    # --- DB ---
    cnx = get_connection()
    cur = cnx.cursor()
    try:
        cur.execute("DELETE FROM Data_balance_rec WHERE caso_id = %s", (caso_id,))
        insert_sql = """
            INSERT INTO Data_balance_rec
            (Flujo, Masa_medida, Masa_recon, Error_masa,
             Ley_medida_Cu, Ley_recon_Cu, Error_ley_Cu,
             id_flujo, Codigo, Masa_Medida2,
             Cu, FCu, Tolerancia, Tolerancia_cu,
             caso_id, fecha_bm)
            VALUES
            (%s, %s, %s, %s,
             %s, %s, %s,
             %s, %s, %s,
             %s, %s, %s, %s,
             %s, %s)
        """
        cur.executemany(insert_sql, rows)
        cnx.commit()
        return len(rows)
    except Exception:
        cnx.rollback()
        raise
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

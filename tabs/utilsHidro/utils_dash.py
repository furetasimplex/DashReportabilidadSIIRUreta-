import base64
import io
import os
import pandas as pd
import plotly_express as px
import numpy as np
import string
import sqlalchemy
#from databricks import sql
import mariadb
import sys
import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mysql.connector
import os
from dotenv import load_dotenv
from dash import Dash
from db_connection import get_connection,get_engine
load_dotenv()

app = Dash(__name__, suppress_callback_exceptions=True)
SSschema = os.getenv("SQLSERVER_SCHEMA", "")
def get_data_agua_casos_hidro(inicio, final, crea_caso):
    ddf_casos = pd.DataFrame()  # Inicializar por seguridad
    db = get_connection()

    if not db:
        print("❌ No se pudo establecer conexión con la base de datos.")
        return ddf_casos

    try:
        # Normalizar schema
        schema_prefix = SSschema if SSschema.endswith(".") else SSschema + "."

        with db.cursor() as cursor:
            if crea_caso == "Si":
                sql_in = f"""
                INSERT INTO {schema_prefix}casos_balance ([fecha], [modelo], [fecha_ini])
                VALUES ('{final}', 2, '{inicio}');
                """
                print("📝 Ejecutando INSERT:")
                print(sql_in)
                try:
                    cursor.execute(sql_in)
                    db.commit()
                    print("✅ Insert correcto en casos_balance.")
                except Exception as e:
                    print("❌ Error al insertar en casos_balance:", e)

            sql = f"""
            SELECT caso_id, fecha, comentarios, modelo, fecha_ini, nombre_caso
            FROM {schema_prefix}casos_balance
            WHERE fecha = '{final}' AND modelo = 2;
            """
            print("🔍 Ejecutando SELECT:")
            print(sql)

            try:
                cursor.execute(sql)
                registros = cursor.fetchall()
                if not registros:
                    print("⚠️ No se encontraron registros para la fecha:", final)
                    return pd.DataFrame()
                print(registros)
                column_names = [desc[0] for desc in cursor.description]
                # ✅ Convertir cada fila a tupla o lista
                rows = [tuple(r) for r in registros]
                ddf_casos = pd.DataFrame(rows, columns=column_names)
                print("📊 Datos de casos:", ddf_casos)
            except Exception as e:
                print("❌ Error al ejecutar SELECT:", e)

    except Exception as e:
        print("💥 Error inesperado en get_data_agua_casos:", e)

    return ddf_casos

def get_agua_his_casos_hidro (final):
     db=get_connection()
     sql2=f"select caso_id, fecha, comentarios, modelo, fecha_ini, nombre_caso " \
        f"FROM {SSschema}casos_balance where modelo=2 order by fecha desc"
        #print(sql)
     cursor = db.cursor()
     try:
            cursor.execute(sql2)
            registros = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            # ✅ Convertir cada fila a tupla o lista
            rows = [tuple(r) for r in registros]
            ddf_casosh = pd.DataFrame(rows, columns=column_names)
            print(ddf_casosh)
     except:
            print("Error en la consulta")
     #db.close()
     return ddf_casosh

def get_fig_bal_casos_hidro(maxid,agg_tab2):
    print("📁 Ruta actual:", os.getcwd())
    
    image_path = "assets/HIDR 2.png"
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
    data_sql =     f'''SELECT
                    flujo_caso_coord.ID, 
                    flujo_caso_coord.id_flujo, 
                    flujo_caso_coord.Etiqueta, 
                    flujo_caso_coord.Descripcion, 
                    flujo_caso_coord.fecha, 
                    flujo_caso_coord.X, 
                    flujo_caso_coord.Y, 
                    flujo_caso_coord.modelo, 
                    flujo_caso_coord.Medido, 
                    flujo_caso_coord.Reconciliado, 
                    flujo_caso_coord.Tolerancia, 
                    flujo_caso_coord.caso
                FROM
                    {SSschema}flujo_caso_coord
                WHERE
                    flujo_caso_coord.caso = '''+ str(maxid) +''' AND
                    flujo_caso_coord.modelo = 2'''
    print(data_sql)
    cursor = db.cursor()
    try:
            cursor.execute(data_sql)
            registros = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            rows = [tuple(r) for r in registros]
            df = pd.DataFrame(rows, columns=column_names)
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

    for _, row in df.iterrows():
        x, y, value = row["X"], row["Y"], round(row[agg_tab2], 2)
        ax.text(x, y, f"{value:.2f}", color="black", fontsize=18 , weight="bold")

    ax.axis("off")

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.savefig("diagrama_hidro.png")
    plt.close(fig)

    return f"data:image/png;base64,{img_base64}"

def get_data_save_casos_hidro(dat_casos,final,maxcas):
        #column_names = [desc[0] for desc in dat_casos.description]
        df = pd.DataFrame(dat_casos)
        print(df)
        # Generar sentencias UPDATE
        tabla = "casos_balance"  # Nombre de la tabla en MySQL
        update_statements = []

        for _, row in df.iterrows():
            set_values = ", ".join([f"{col} = '{row[col]}'" if isinstance(row[col], str) else f"{col} = {row[col]}" for col in df.columns if col != 'caso_id'])
            update_statements.append(f"UPDATE {SSschema}{tabla} SET {set_values} WHERE caso_id = {maxcas};")

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
                #finally:
                   # cursor.close()
        return 

def get_data_publica_casos_hidro (dat_casos,rec_caso, maxcas):
    db=get_connection()
    df_tot = pd.DataFrame(dat_casos)
    df = df_tot[df_tot['caso_id'] == maxcas]
    print(df)
    df_rec = pd.DataFrame(rec_caso)
    id_caso=df.iloc[0, 0]
    fecha_caso=df.iloc[0, 1]
    modelo_caso=df.iloc[0, 3]
    tabla = "data_balance"  # Nombre de la tabla en MySQL

    df_rec['caso']=id_caso
    df_rec['modelo']=modelo_caso
    df_rec['fecha']=fecha_caso
    df_rec['unidad']="l/s"
    df_rec.rename(columns={'Flujo':'Proceso_Concentradora','Codigo':'Flujos', 'Masa Medida':'Medido', 'Masa recon':'Reconciliado' , 'Porcentaje Ajuste':'por_Variación' }, inplace=True)
    df_rec=df_rec.fillna(0)

    query = f"delete from {SSschema}{tabla} where caso={id_caso};"
    print(query)

 
    cursor = db.cursor()
    try:
                    cursor.execute(query)
                    db.commit()                
    except:
                    print("Error en borrado ")         
    finally:
                cursor.close()
  
    update_statements = []

    columnas = ", ".join(df_rec.columns)
    valores = ", ".join(
        "(" + ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in row]) + ")"
        for row in df_rec.itertuples(index=False, name=None)
    )

    query = f"INSERT INTO {SSschema}{tabla} ({columnas}) VALUES {valores};"
    print(query)

 
    cursor = db.cursor()
    try:
                    cursor.execute(query)
                    db.commit()
                    
    except:
                    print("Error en la publicacion ")         
    finally:
                cursor.close()        
    return 

     
#   get_data_save_tags     

def get_data_save_tags_hidro(inicio, fin, dat_tags):
        #column_names = [desc[0] for desc in dat_casos.description]
        df = pd.DataFrame(dat_tags)
        #print(df)
        inicio_tag = inicio 
        final_tag  = fin 

        tabla = "Tags_SGO"  # Nombre de la tabla en MySQL

        df = df.iloc[:, 0:-1]
        df_rec=df.fillna(0)
        
        
        df_rec.info()

        query = f"delete from {SSschema}{tabla} where Fini between '{inicio_tag}' and '{final_tag}';"
        print(query)
        db=get_connection()

 
        cursor = db.cursor()
        try:
                        cursor.execute(query)
                        db.commit()
                        
        except:
                        print("Error en borrado ")    
        finally:
                cursor.close()                     
        print('grabado ok')
        # Generar sentencias UPDATE
    #tabla = "data_balance"  # Nombre de la tabla en MySQL
    # data_id	caso	modelo	fecha	Flujos	 Proceso_Concentradora	unidad	Medido	Reconciliado	Diferencia	por_Variación	Tolerancia
    #Codigo  Flujo  Masa Medida  Masa recon  Tolerancia  Diferencia  Porcentaje Ajuste  caso  modelo       fecha unidad
        update_statements = []

        columnas = ", ".join(df_rec.columns)
        valores = ", ".join(
            "(" + ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in row]) + ")"
            for row in df_rec.itertuples(index=False, name=None)
        )


        query = f"INSERT INTO {SSschema}{tabla} ({columnas}) VALUES {valores};"
        #print(query)

    
        cursor = db.cursor()
        try:
                        cursor.execute(query)
                        db.commit()
                        
        except Exception as e:
                        print("Error en la publicacion tags  ", e)   
        finally:
                cursor.close()                      
                
        return 



# *********


def get_nombre_app_hidro():
    return 'Balance Agua Hidrometalurgia Spence'


def parse_contents_hidro(contents, filename):
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

def local_img_to_html_hidro(path,img_name):
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



def carta_control_hidro(df, x_col, y_col, titulo="Carta de Control", N=3, destacar_outliers=True, metodo="STD"):
    """
    Genera una carta de control estadístico de procesos.

    Args:
        df (pd.DataFrame): DataFrame con los datos.
        x_col (str): Nombre de la columna para el eje X (fecha o tiempo).
        y_col (str): Nombre de la columna para el eje Y (medida).
        N (int): Número de desviaciones estándar o múltiplos del IQR. Por defecto 3.
        destacar_outliers (bool): Si es True, resalta los puntos fuera de los límites.
        metodo (str): Método para calcular límites y tendencia central ("STD" o "IQR").

    Returns:
        fig (plotly.graph_objects.Figure): Figura de la carta de control.
    """
    # Verificar método válido
    if metodo not in ["STD", "IQR"]:
        raise ValueError("El método debe ser 'STD' o 'IQR'.")
    
    # Calcular límites y tendencia central según el método seleccionado
    if metodo == "STD":
        tendencia_label = "Media"
        tendencia_central = df[y_col].mean()
        dispersion = df[y_col].std()
        lcl = tendencia_central - N * dispersion  # Límite inferior
        ucl = tendencia_central + N * dispersion  # Límite superior
    elif metodo == "IQR":
        tendencia_label = "Mediana"
        q1 = df[y_col].quantile(0.25)
        q3 = df[y_col].quantile(0.75)
        iqr = q3 - q1
        tendencia_central = df[y_col].median()
        lcl = q1 - N * iqr  # Límite inferior
        ucl = q3 + N * iqr  # Límite superior

    # Identificar outliers si está habilitado
    if destacar_outliers:
        df['outlier'] = np.where((df[y_col] > ucl) | (df[y_col] < lcl), 'Outlier', 'Dentro de control')

    # Crear el gráfico
    if destacar_outliers:
        fig = px.scatter(
            df, x=x_col, y=y_col, marginal_y="histogram",
            color='outlier',  # Resalta los outliers
            color_discrete_map={
                'Outlier': 'red', 
                'Dentro de control': 'blue'
            },
            title=titulo #f"Carta de Control Estadístico ({metodo})"
        )
    else:
        fig = px.scatter(
            df, x=x_col, y=y_col, marginal_y="histogram",
            title=titulo #f"Carta de Control Estadístico ({metodo})"
        )
    
    # Ocultar la leyenda de colores
    fig.update_traces(showlegend=False)

    # Agregar líneas de control y la tendencia central
    fig.add_hline(y=tendencia_central, line_dash="dash", line_color="blue", annotation_text=tendencia_label, annotation_position="bottom right")
    fig.add_hline(y=ucl, line_dash="dot", line_color="green", annotation_text=f"UCL (+{N}{'σ' if metodo == 'STD' else 'IQR'})", annotation_position="top right")
    fig.add_hline(y=lcl, line_dash="dot", line_color="red", annotation_text=f"LCL (-{N}{'σ' if metodo == 'STD' else 'IQR'})", annotation_position="bottom right")

    # Ajustar diseño
    fig.update_layout(
        xaxis_title=x_col,
        yaxis_title=y_col,
        template="plotly_white"
    )

    return fig

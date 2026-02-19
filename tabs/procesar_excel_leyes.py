import pandas as pd
import numpy as np
import datetime
import re
import unicodedata
from sqlalchemy import text
from db_connection import get_engine

# ==============================================================================
# CONFIGURACIÓN DE LA BASE DE DATOS
# ¡VERIFICA ESTO! Si tu tabla se llama distinto, cámbialo aquí.
# ==============================================================================
DB_SCHEMA = 'inventar_SpcHidr'   # Ejemplo: 'dbo' o 'inventar_SpcHidr'
DB_TABLE  = 'Informe_TM_lab'     # Ejemplo: 'tu_tabla_granulometria'

# ==============================================================================
# MAPEOS Y UTILIDADES
# ==============================================================================
MAPA_MALLAS = {
    '2"': '2P', '1"': '1P', '3/4"': '3_4P', '1/2"': '1_2P', '1/4"': '1_4P',
    '# 10': '10m', '# 35': '35m', '# 100': '100m', '# 150': '150m',
    '# 200': '200m', '# 325': '325m', '- # 325': 'Bajo325m', 'Total': None,
}

PESO_COLS = [
    "Peso_2P", "Peso_1P", "Peso_3_4P", "Peso_1_2P", "Peso_1_4P",
    "Peso_10m", "Peso_35m", "Peso_100m", "Peso_150m", "Peso_200m",
    "Peso_325m", "Peso_Bajo325m"
]

def _strip_accents(s: str) -> str:
    if s is None: return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s

def _norm_text(x) -> str:
    if x is None or pd.isna(x): return ""
    s = str(x).strip()
    s = _strip_accents(s).lower()
    return " ".join(s.split())

def clean_num(valor):
    if valor is None or pd.isna(valor): return None
    if isinstance(valor, (int, float, np.integer, np.floating)):
        try: return float(valor)
        except: return None
    try:
        s = str(valor).strip().replace(",", ".")
        if not re.match(r"^-?\d+(?:\.\d+)?$", s): return None
        return float(s)
    except: return None

def normalizar_hora(valor):
    if valor is None or pd.isna(valor): return None
    if isinstance(valor, (datetime.datetime, pd.Timestamp)): return valor.time()
    if isinstance(valor, datetime.time): return valor
    try:
        s = str(valor).strip()
        if not s: return None
        dt = pd.to_datetime(s, errors="coerce")
        if pd.isna(dt): return None
        return dt.time()
    except: return None

def value_right_any(df, r, c, max_step=3):
    for step in range(1, max_step + 1):
        try:
            v = df.iat[r, c + step]
            if v is not None and not pd.isna(v) and str(v).strip() != "":
                return v
        except: continue
    return None

def value_right_first_numeric(df, r, c, max_step=6):
    for step in range(1, max_step + 1):
        try:
            v = df.iat[r, c + step]
            num = clean_num(v)
            if num is not None: return num
        except: continue
    return None

def find_first_cell_norm(df, needle_norm, r0=0, r1=None, c0=0, c1=None):
    if r1 is None: r1 = len(df)
    if c1 is None: c1 = df.shape[1]
    sub = df.iloc[r0:r1, c0:c1]
    for rr in range(sub.shape[0]):
        for cc in range(sub.shape[1]):
            if needle_norm in _norm_text(sub.iat[rr, cc]):
                return (r0 + rr, c0 + cc)
    return (None, None)

def find_exact_cell_norm(df, needle_norm, r0=0, r1=None, c0=0, c1=None):
    if r1 is None: r1 = len(df)
    if c1 is None: c1 = df.shape[1]
    sub = df.iloc[r0:r1, c0:c1]
    for rr in range(sub.shape[0]):
        for cc in range(sub.shape[1]):
            if _norm_text(sub.iat[rr, cc]) == needle_norm:
                return (r0 + rr, c0 + cc)
    return (None, None)

def get_quim_table_window(df_bloque, r0=0, r1=250):
    r1 = min(r1, len(df_bloque))
    c1 = df_bloque.shape[1]
    rr, cc = find_first_cell_norm(df_bloque, _norm_text("Informe de Ensayos Quimicos"), r0=r0, r1=r1, c0=0, c1=c1)
    if rr is None: return r0, min(r0 + 140, len(df_bloque)), 0, c1
    return rr, min(rr + 60, len(df_bloque)), max(cc - 2, 0), min(cc + 6, c1)

def first_nonempty_cell_text(row) -> str:
    for v in row:
        if v is not None and not pd.isna(v) and str(v).strip() != "":
            return str(v).strip()
    return ""

def detectar_inicios_turno(df_hoja):
    starts = []
    for idx, row in df_hoja.iterrows():
        head = first_nonempty_cell_text(row.values)
        head_norm = _norm_text(head)
        if head_norm.startswith("turno"):
            if '"a"' in head_norm or " a" in head_norm: starts.append(("A", idx))
            elif '"b"' in head_norm or " b" in head_norm: starts.append(("B", idx))
    return starts

def es_registro_valido_granulometria(data: dict) -> bool:
    if not data or not isinstance(data, dict): return False
    for k in PESO_COLS:
        v = data.get(k)
        if v is not None and clean_num(v) is not None and clean_num(v) > 0:
            return True
    return False

# ==============================================================================
# LÓGICA DE EXTRACCIÓN DE FECHAS
# ==============================================================================
def extraer_fecha_header_global(df_hoja):
    # Busca fechas tipo 31-01-2026 o 01/02/2026 en las primeras 10 filas
    regex_fecha = re.compile(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})")
    try:
        filas_revisar = min(10, len(df_hoja))
        for r in range(filas_revisar):
            for c in range(len(df_hoja.columns)):
                celda = str(df_hoja.iloc[r, c]).strip()
                match = regex_fecha.search(celda)
                if match:
                    dia, mes, anio = match.groups()
                    try: return datetime.date(int(anio), int(mes), int(dia))
                    except ValueError: continue
    except Exception as e:
        print(f"Advertencia header global: {e}")
    return None

def extraer_metadata_turno(df_bloque):
    metadata = {"Fecha_Toma_Muestra": None, "Hora_Toma_Muestra": None, "Fecha_Recepcion": None, "Fecha_Informe": None}
    busquedas = {
        "Fecha Toma de Muestra": "Fecha_Toma_Muestra", "Hora Toma de Muestra": "Hora_Toma_Muestra",
        "Fecha Recepción de Muestra": "Fecha_Recepcion", "Fecha de Informe": "Fecha_Informe"
    }
    try:
        filas_a_revisar = min(20, len(df_bloque))
        for r in range(filas_a_revisar):
            for c in range(len(df_bloque.columns) - 1):
                celda = str(df_bloque.iloc[r, c]).strip()
                for texto_excel, clave_dict in busquedas.items():
                    if texto_excel.lower() in celda.lower():
                        valor = value_right_any(df_bloque, r, c, max_step=2)
                        if pd.notnull(valor):
                            if "Hora" in clave_dict:
                                metadata[clave_dict] = str(valor).split('.')[0].strip()
                            elif "Fecha" in clave_dict:
                                try: metadata[clave_dict] = pd.to_datetime(valor).date()
                                except: metadata[clave_dict] = None
                        break
    except Exception as e:
        print(f"Advertencia metadata: {e}")
    return metadata

def extraer_datos_bloque(df_bloque, torre, turno):
    now_ts = datetime.datetime.now()
    data = {
        "Torre": torre, "Fecha": None, "Hora": None, "Turno": turno,
        "Realizada_Por": None, "Analista": None, "Obs_General": None,
        "Peso_Total_kg": None, "Peso_Rechazo_kg": None, "Peso_Quimico_kg": None, "Peso_Inicial_g": None,
        "Humedad_1_Pct": None, "Humedad_2_Pct": None, "Humedad_Prom_Pct": None,
        "CuT_global": None, "CuS_Global": None, "Fe_Global": None, "FeS_Global": None,
        "Carb_Global": None, "Cl_KgTon": None, "Cons_KgTon": None, "CuFe_Global": None,
        "Fecha_Carga": now_ts,
    }

    r0, r1 = 0, min(140, len(df_bloque))
    c0, c1 = 0, df_bloque.shape[1]

    # Datos Generales
    for label, key in [("Realizada por", "Realizada_Por"), ("Analista Quimico", "Analista"),
                       ("Fecha Toma de Muestra", "Fecha"), ("Observaciones", "Obs_General")]:
        rr, cc = find_first_cell_norm(df_bloque, _norm_text(label), r0=r0, r1=r1, c0=c0, c1=c1)
        if rr is not None: data[key] = value_right_any(df_bloque, rr, cc)

    # Hora
    rr, cc = find_first_cell_norm(df_bloque, _norm_text("Hora Toma de Muestra"), r0=r0, r1=r1, c0=c0, c1=c1)
    if rr is not None: data["Hora"] = normalizar_hora(value_right_any(df_bloque, rr, cc))

    # Pesos
    for label, key in [("Peso Total", "Peso_Total_kg"), ("Peso Rechazo", "Peso_Rechazo_kg"),
                       ("Peso Quimico", "Peso_Quimico_kg"), ("Peso Inicial", "Peso_Inicial_g"),
                       ("N°1 %Humedad", "Humedad_1_Pct"), ("N°2 %Humedad", "Humedad_2_Pct"),
                       ("Promedio %Humedad", "Humedad_Prom_Pct")]:
        rr, cc = find_first_cell_norm(df_bloque, _norm_text(label), r0=r0, r1=r1, c0=c0, c1=c1)
        if rr is not None: data[key] = clean_num(value_right_any(df_bloque, rr, cc))

    # Quimicos
    qr0, qr1, qc0, qc1 = get_quim_table_window(df_bloque, r0=0, r1=r1)
    for label, key in [("CuT", "CuT_global"), ("CuS", "CuS_Global"), ("Fe", "Fe_Global"), ("FeS", "FeS_Global"),
                       ("Carbonato", "Carb_Global"), ("Cloruro Acido", "Cl_KgTon"), ("Consumo Acido", "Cons_KgTon"),
                       ("CuFe", "CuFe_Global")]:
        lab = _norm_text(label)
        rr, cc = find_exact_cell_norm(df_bloque, lab, r0=qr0, r1=qr1, c0=qc0, c1=qc1)
        if rr is None: rr, cc = find_first_cell_norm(df_bloque, lab, r0=qr0, r1=qr1, c0=qc0, c1=qc1)
        if rr is not None: data[key] = value_right_first_numeric(df_bloque, rr, cc)

    # Granulometria
    rm, cm = find_first_cell_norm(df_bloque, _norm_text("MALLA"), r0=0, r1=min(250, len(df_bloque)), c0=0, c1=c1)
    if rm is not None:
        header_row = df_bloque.iloc[rm, :].tolist()
        def find_col(needle):
            nn = _norm_text(needle)
            for j, v in enumerate(header_row):
                if nn in _norm_text(v): return j
            return None
        
        col_peso, col_rp = find_col("Peso Retenido"), find_col("Retenido Parcial")
        col_ra, col_pas = find_col("Retenido Acumulado"), find_col("Pasante Acumulado")
        col_cut = find_col("CuT")
        if col_cut is None: _, col_cut = find_first_cell_norm(df_bloque, _norm_text("CuT"), r0=rm, r1=min(rm+5, len(df_bloque)), c0=0, c1=c1)
        
        # Fallbacks si no encuentra columnas
        if col_peso is None: col_peso = cm + 1
        if col_rp is None: col_rp = cm + 2
        if col_ra is None: col_ra = cm + 3
        if col_pas is None: col_pas = cm + 4
        if col_cut is None: col_cut = cm + 5

        vacias = 0
        for i in range(1, 80):
            rrow = rm + i
            if rrow >= len(df_bloque): break
            raw_malla = df_bloque.iat[rrow, cm] if cm < c1 else None
            nombre = str(raw_malla).strip() if raw_malla is not None and not pd.isna(raw_malla) else ""
            if not nombre:
                vacias += 1
                if vacias >= 3: break
                continue
            vacias = 0
            suf = MAPA_MALLAS.get(nombre.replace('"""', '"').replace('""', '"'), None)
            if suf:
                def safe_get(c): return clean_num(df_bloque.iat[rrow, c]) if c < df_bloque.shape[1] else None
                data[f"Peso_{suf}"] = safe_get(col_peso)
                data[f"RetParcial_{suf}"] = safe_get(col_rp)
                data[f"RetAcum_{suf}"] = safe_get(col_ra)
                data[f"Pasante_{suf}"] = safe_get(col_pas)
                data[f"CuT_{suf}"] = safe_get(col_cut)
    return data

# ==============================================================================
# FUNCIÓN PRINCIPAL
# ==============================================================================
def procesar_excel_multih(file_content, filename, dias_seleccionados):
    engine = get_engine()
    registros = []
    
    procesar_todo = (dias_seleccionados == "all")
    dias_obj = [] if procesar_todo else [int(d) for d in dias_seleccionados]
    
    torre = "T2" if ("N2" in filename.upper() or "TORRE 2" in filename.upper()) else "T1"

    try:
        xls = pd.ExcelFile(file_content)
    except Exception as e:
        return f"Error crítico leyendo Excel: {e}"

    hojas_map = {str(h).strip(): h for h in xls.sheet_names}
    
    for dia in range(1, 32):
        if not procesar_todo and dia not in dias_obj: continue
        
        # Busca hoja "1" o "01"
        dia_str, dia_pad = str(dia), str(dia).zfill(2)
        nombre_hoja = hojas_map.get(dia_str) or hojas_map.get(dia_pad)
        
        if not nombre_hoja: continue

        try:
            df = pd.read_excel(xls, sheet_name=nombre_hoja, header=None)
            fecha_header = extraer_fecha_header_global(df)
            starts = detectar_inicios_turno(df)
            
            if not starts: continue

            for i, (turno, ini) in enumerate(starts):
                fin = starts[i+1][1] if i+1 < len(starts) else len(df)
                df_bloque = df.iloc[ini:fin].reset_index(drop=True)
                
                reg = extraer_datos_bloque(df_bloque, torre, turno)
                reg.update(extraer_metadata_turno(df_bloque))
                
                # Prioridad de fecha
                reg["Fecha"] = reg.get("Fecha_Toma_Muestra") or reg.get("Fecha_Recepcion") or reg.get("Fecha_Informe") or fecha_header
                reg["Fecha_Carga"] = datetime.datetime.now()

                if reg["Fecha"] is not None:
                    registros.append(reg)

        except Exception as e:
            print(f"Error procesando {nombre_hoja}: {e}")
            continue

    if not registros:
        return f"⚠️ No se encontraron datos válidos."

    # Guardar en BD con Anti-Duplicados
    try:
        df_out = pd.DataFrame(registros)
        if "ID_Registro" in df_out.columns: df_out = df_out.drop(columns=["ID_Registro"])
        
        # Filtramos fechas únicas para borrar duplicados previos
        fechas_unicas = df_out['Fecha'].unique()
        
        # Formateamos fechas a YYYYMMDD para que SQL Server no se confunda
        fechas_sql = "', '".join([f.strftime('%Y%m%d') for f in fechas_unicas if f is not None])
        
        if fechas_sql:
            query_borrar = text(f"DELETE FROM {DB_SCHEMA}.{DB_TABLE} WHERE Torre = :torre AND Fecha IN ('{fechas_sql}')")
            with engine.connect() as conn:
                conn.execute(query_borrar, {"torre": torre})
                conn.commit()

        df_out.to_sql(name=DB_TABLE, schema=DB_SCHEMA, con=engine, if_exists='append', index=False)
        return f"✅ Éxito: Se actualizaron {len(df_out)} registros en {DB_TABLE} (Torre {torre})."

    except Exception as e:
        return f"❌ Error Base de Datos: {e}"
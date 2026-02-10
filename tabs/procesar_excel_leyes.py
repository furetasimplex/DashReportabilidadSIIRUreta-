import pandas as pd
import numpy as np
import datetime
import re
import unicodedata

from db_connection import get_engine

# =========================
# Mapeo de mallas (Excel -> sufijo SQL)
# =========================
MAPA_MALLAS = {
    '2"': '2P',
    '1"': '1P',
    '3/4"': '3_4P',
    '1/2"': '1_2P',
    '1/4"': '1_4P',
    '# 10': '10m',
    '# 35': '35m',
    '# 100': '100m',
    '# 150': '150m',
    '# 200': '200m',
    '# 325': '325m',
    '- # 325': 'Bajo325m',
    'Total': None,
}

# Campos granulometría (para validación fuerte)
PESO_COLS = [
    "Peso_2P", "Peso_1P", "Peso_3_4P", "Peso_1_2P", "Peso_1_4P",
    "Peso_10m", "Peso_35m", "Peso_100m", "Peso_150m", "Peso_200m",
    "Peso_325m", "Peso_Bajo325m"
]

# =========================
# Utilidades base
# =========================
def _strip_accents(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s

def _norm_text(x) -> str:
    if x is None or pd.isna(x):
        return ""
    s = str(x).strip()
    s = _strip_accents(s).lower()
    s = " ".join(s.split())
    return s

def clean_num(valor):
    """Convierte a float si es numérico; si no retorna None."""
    if valor is None or pd.isna(valor):
        return None
    if isinstance(valor, (int, float, np.integer, np.floating)):
        try:
            return float(valor)
        except:
            return None
    try:
        s = str(valor).strip().replace(",", ".")
        if s == "":
            return None
        if not re.match(r"^-?\d+(?:\.\d+)?$", s):
            return None
        return float(s)
    except:
        return None

def normalizar_hora(valor):
    if valor is None or pd.isna(valor):
        return None
    if isinstance(valor, (datetime.datetime, pd.Timestamp)):
        return valor.time()
    if isinstance(valor, datetime.time):
        return valor
    try:
        s = str(valor).strip()
        if not s:
            return None
        dt = pd.to_datetime(s, errors="coerce")
        if pd.isna(dt):
            return None
        return dt.time()
    except:
        return None

def value_right_any(df, r, c, max_step=3):
    """
    Retorna el primer valor no vacío entre (c+1 .. c+max_step).
    """
    for step in range(1, max_step + 1):
        try:
            v = df.iat[r, c + step]
            if v is None or pd.isna(v) or str(v).strip() == "":
                continue
            return v
        except:
            continue
    return None

def value_right_first_numeric(df, r, c, max_step=6):
    """
    Retorna el primer valor numérico a la derecha de (r,c),
    ignorando unidades como '%', 'kg/ton', etc.
    """
    for step in range(1, max_step + 1):
        try:
            v = df.iat[r, c + step]
        except:
            continue
        num = clean_num(v)
        if num is not None:
            return num
    return None

def find_first_cell_norm(df, needle_norm, r0=0, r1=None, c0=0, c1=None):
    """
    Encuentra primera celda cuyo texto normalizado CONTIENE needle_norm.
    """
    if r1 is None:
        r1 = len(df)
    if c1 is None:
        c1 = df.shape[1]

    sub = df.iloc[r0:r1, c0:c1]
    for rr in range(sub.shape[0]):
        for cc in range(sub.shape[1]):
            if needle_norm in _norm_text(sub.iat[rr, cc]):
                return (r0 + rr, c0 + cc)
    return (None, None)

def find_exact_cell_norm(df, needle_norm, r0=0, r1=None, c0=0, c1=None):
    """
    Encuentra celda cuyo texto normalizado es EXACTAMENTE needle_norm.
    """
    if r1 is None:
        r1 = len(df)
    if c1 is None:
        c1 = df.shape[1]

    sub = df.iloc[r0:r1, c0:c1]
    for rr in range(sub.shape[0]):
        for cc in range(sub.shape[1]):
            if _norm_text(sub.iat[rr, cc]) == needle_norm:
                return (r0 + rr, c0 + cc)
    return (None, None)

def get_quim_table_window(df_bloque, r0=0, r1=250):
    """
    Ventana del panel de ensayos químicos (lado derecho).
    Restringe columnas alrededor del encabezado "Informe de Ensayos Químicos"
    para evitar confundir CuT (químico) con CuT (granulometría).
    """
    r1 = min(r1, len(df_bloque))
    c1 = df_bloque.shape[1]

    rr, cc = find_first_cell_norm(
        df_bloque,
        _norm_text("Informe de Ensayos Quimicos"),
        r0=r0, r1=r1, c0=0, c1=c1
    )

    if rr is None:
        # fallback conservador
        return r0, min(r0 + 140, len(df_bloque)), 0, c1

    # ✅ Panel derecho: normalmente parte cerca de la columna del encabezado
    qc0 = max(cc - 2, 0)
    qc1 = min(cc + 6, c1)   # 6 columnas suele cubrir: etiqueta, unidad, valor
    qr0 = rr
    qr1 = min(rr + 60, len(df_bloque))  # suficiente para la tabla química completa

    return qr0, qr1, qc0, qc1

def first_nonempty_cell_text(row) -> str:
    for v in row:
        if v is None or pd.isna(v):
            continue
        s = str(v).strip()
        if s != "":
            return s
    return ""

def detectar_inicios_turno(df_hoja):
    starts = []
    for idx, row in df_hoja.iterrows():
        head = first_nonempty_cell_text(row.values)
        head_norm = _norm_text(head)
        if head_norm.startswith("turno"):
            if '"a"' in head_norm or " a" in head_norm:
                starts.append(("A", idx))
            elif '"b"' in head_norm or " b" in head_norm:
                starts.append(("B", idx))
    return starts

def es_registro_valido_granulometria(data: dict) -> bool:
    """
    Exportar SOLO si hay granulometría real:
      - al menos un Peso_* numérico > 0
    """
    if not data or not isinstance(data, dict):
        return False
    for k in PESO_COLS:
        v = data.get(k)
        if v is not None:
            try:
                if float(v) > 0:
                    return True
            except:
                pass
    return False


# =========================
# Extracción por bloque (Turno A/B)
# =========================
def extraer_datos_bloque(df_bloque, torre, turno):
    now_ts = datetime.datetime.now()

    data = {
        "Torre": torre,
        "Fecha": None,
        "Hora": None,
        "Turno": turno,
        "Realizada_Por": None,
        "Analista": None,
        "Obs_General": None,

        "Peso_Total_kg": None,
        "Peso_Rechazo_kg": None,
        "Peso_Quimico_kg": None,
        "Peso_Inicial_g": None,

        "Humedad_1_Pct": None,
        "Humedad_2_Pct": None,
        "Humedad_Prom_Pct": None,

        "CuT_global": None,   # si tu BD no tiene esta columna, eliminar esta línea + su grab
        "CuS_Global": None,
        "Fe_Global": None,
        "FeS_Global": None,
        "Carb_Global": None,
        "Cl_KgTon": None,
        "Cons_KgTon": None,
        "CuFe_Global": None,

        "Fecha_Carga": now_ts,
    }

    r0 = 0
    r1 = min(140, len(df_bloque))
    c0 = 0
    c1 = df_bloque.shape[1]

    # --- Cabeceras ---
    r, c = find_first_cell_norm(df_bloque, _norm_text("Realizada por"), r0=r0, r1=r1, c0=c0, c1=c1)
    if r is not None:
        data["Realizada_Por"] = value_right_any(df_bloque, r, c, max_step=3)

    r, c = find_first_cell_norm(df_bloque, _norm_text("Analista Quimico"), r0=r0, r1=r1, c0=c0, c1=c1)
    if r is not None:
        data["Analista"] = value_right_any(df_bloque, r, c, max_step=3)

    r, c = find_first_cell_norm(df_bloque, _norm_text("Fecha Toma de Muestra"), r0=r0, r1=r1, c0=c0, c1=c1)
    if r is not None:
        data["Fecha"] = value_right_any(df_bloque, r, c, max_step=3)

    r, c = find_first_cell_norm(df_bloque, _norm_text("Hora Toma de Muestra"), r0=r0, r1=r1, c0=c0, c1=c1)
    if r is not None:
        data["Hora"] = normalizar_hora(value_right_any(df_bloque, r, c, max_step=3))

    r, c = find_first_cell_norm(df_bloque, _norm_text(f"Observaciones T/{turno}"), r0=r0, r1=r1, c0=c0, c1=c1)
    if r is None:
        r, c = find_first_cell_norm(df_bloque, _norm_text("Observaciones"), r0=r0, r1=r1, c0=c0, c1=c1)
    if r is not None:
        obs = value_right_any(df_bloque, r, c, max_step=3)
        data["Obs_General"] = str(obs).strip() if obs is not None and str(obs).strip() != "" else None

    # --- Pesos/Humedad ---
    def grab_num(label, key):
        rr, cc = find_first_cell_norm(df_bloque, _norm_text(label), r0=r0, r1=r1, c0=c0, c1=c1)
        if rr is not None:
            data[key] = clean_num(value_right_any(df_bloque, rr, cc, max_step=3))

    grab_num("Peso Total", "Peso_Total_kg")
    grab_num("Peso Rechazo", "Peso_Rechazo_kg")
    grab_num("Peso Quimico", "Peso_Quimico_kg")
    grab_num("Peso Inicial", "Peso_Inicial_g")
    grab_num("N°1 %Humedad", "Humedad_1_Pct")
    grab_num("N°2 %Humedad", "Humedad_2_Pct")
    grab_num("Promedio %Humedad", "Humedad_Prom_Pct")

    # --- Químicos (panel específico + match exacto para evitar "Fe" vs "Fecha") ---
    qr0, qr1, qc0, qc1 = get_quim_table_window(df_bloque, r0=0, r1=r1)

    def grab_quim_exact(label, key):
        lab = _norm_text(label)
        rr, cc = find_exact_cell_norm(df_bloque, lab, r0=qr0, r1=qr1, c0=qc0, c1=qc1)
        if rr is None:
            rr, cc = find_first_cell_norm(df_bloque, lab, r0=qr0, r1=qr1, c0=qc0, c1=qc1)
        if rr is not None:
            data[key] = value_right_first_numeric(df_bloque, rr, cc, max_step=6)

    grab_quim_exact("CuT", "CuT_global")
    grab_quim_exact("CuS", "CuS_Global")
    grab_quim_exact("Fe", "Fe_Global")
    grab_quim_exact("FeS", "FeS_Global")
    grab_quim_exact("Carbonato", "Carb_Global")
    grab_quim_exact("Cloruro Acido", "Cl_KgTon")
    grab_quim_exact("Consumo Acido", "Cons_KgTon")
    grab_quim_exact("CuFe", "CuFe_Global")

    # =========================
    # Granulometría (MALLA)
    # =========================
    rm, cm = find_first_cell_norm(df_bloque, _norm_text("MALLA"), r0=0, r1=min(250, len(df_bloque)), c0=0, c1=c1)
    if rm is None:
        return data

    header_row = df_bloque.iloc[rm, :].tolist()

    def find_col_in_header(needle):
        needle_n = _norm_text(needle)
        for j, v in enumerate(header_row):
            if needle_n in _norm_text(v):
                return j
        return None

    col_peso = find_col_in_header("Peso Retenido")
    col_rp   = find_col_in_header("Retenido Parcial")
    col_ra   = find_col_in_header("Retenido Acumulado")
    col_pas  = find_col_in_header("Pasante Acumulado")

    col_cut = find_col_in_header("CuT")
    if col_cut is None:
        rr, cc = find_first_cell_norm(df_bloque, _norm_text("CuT"), r0=rm, r1=min(rm + 5, len(df_bloque)), c0=0, c1=c1)
        col_cut = cc

    if col_peso is None: col_peso = cm + 1
    if col_rp   is None: col_rp   = cm + 2
    if col_ra   is None: col_ra   = cm + 3
    if col_pas  is None: col_pas  = cm + 4
    if col_cut  is None: col_cut  = cm + 5

    vacias = 0
    for i in range(1, 80):
        rrow = rm + i
        if rrow >= len(df_bloque):
            break

        raw_malla = df_bloque.iat[rrow, cm] if cm < c1 else None
        nombre = str(raw_malla).strip() if raw_malla is not None and not pd.isna(raw_malla) else ""
        nombre = nombre.replace('"""', '"').replace('""', '"')

        if not nombre:
            vacias += 1
            if vacias >= 3:
                break
            continue
        vacias = 0

        suf = MAPA_MALLAS.get(nombre, None)
        if not suf:
            continue

        def safe_get(r, c):
            try:
                return df_bloque.iat[r, c]
            except:
                return None

        data[f"Peso_{suf}"] = clean_num(safe_get(rrow, col_peso))
        data[f"RetParcial_{suf}"] = clean_num(safe_get(rrow, col_rp))
        data[f"RetAcum_{suf}"] = clean_num(safe_get(rrow, col_ra))
        data[f"Pasante_{suf}"] = clean_num(safe_get(rrow, col_pas))
        data[f"CuT_{suf}"] = clean_num(safe_get(rrow, col_cut))

    return data


# =========================
# Proceso principal (export a SQL)
# =========================
def procesar_excel_multih(file_like, nombre_archivo, dias_seleccionados):
    try:
        engine = get_engine()
    except Exception as e:
        return f"Error de Conexión BD: {str(e)}"

    torre = "Desconocida"
    n = (nombre_archivo or "").upper()
    if "N1" in n or "TORRE N1" in n or "TORRE  N1" in n:
        torre = "Torre_N1"
    elif "N2" in n or "TORRE N2" in n or "TORRE  N2" in n:
        torre = "Torre_N2"

    try:
        xls = pd.ExcelFile(file_like, engine="openpyxl")
    except Exception as e:
        return f"Error leyendo Excel: {str(e)}"

    dias_ints = []
    for d in dias_seleccionados:
        try:
            dias_ints.append(int(d))
        except:
            pass

    registros = []

    for dia in dias_ints:
        hoja = None
        sd = str(dia)
        for s in xls.sheet_names:
            sc = s.strip()
            if sc == sd or sc == f"0{sd}":
                hoja = s
                break
        if hoja is None:
            continue

        try:
            df = pd.read_excel(xls, sheet_name=hoja, header=None)
        except Exception as e:
            print(f"Error leyendo hoja {hoja}: {e}")
            continue

        starts = detectar_inicios_turno(df)
        if not starts:
            continue

        for i, (turno_letra, ini) in enumerate(starts):
            fin = starts[i + 1][1] if i + 1 < len(starts) else len(df)
            df_bloque = df.iloc[ini:fin].reset_index(drop=True)

            reg = extraer_datos_bloque(df_bloque, torre, turno_letra)

            if reg.get("Fecha") is None:
                try:
                    hoy = datetime.date.today()
                    reg["Fecha"] = datetime.date(hoy.year, hoy.month, int(dia))
                except:
                    pass

            if es_registro_valido_granulometria(reg):
                registros.append(reg)

    if not registros:
        return f"⚠️ No se encontraron registros con granulometría válida en los días seleccionados ({dias_seleccionados})."

    df_out = pd.DataFrame(registros)

    if "ID_Registro" in df_out.columns:
        df_out = df_out.drop(columns=["ID_Registro"])

    df_out = df_out.where(pd.notnull(df_out), None)

    try:
        df_out.to_sql(
            "Informe_TM_lab",
            engine,
            schema="inventar_SpcHidr",
            if_exists="append",
            index=False
        )
        return f"✅ Éxito: Se cargaron {len(df_out)} registros con granulometría ({torre})."
    except Exception as e:
        return f"❌ Error SQL: {str(e)}"

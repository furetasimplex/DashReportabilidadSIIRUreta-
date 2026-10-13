"""SQL de solo lectura; conexión anfitriona inyectada, sin .env propio."""
import re
import numpy as np
import pandas as pd
from sqlalchemy import text
SCHEMA = "inventar_SpcHidr.inventar_SpcHidr"
_engine_provider = None

def configure(engine_provider, schema="inventar_SpcHidr.inventar_SpcHidr"):
    global _engine_provider, SCHEMA
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?", schema):
        raise ValueError("Esquema inválido")
    _engine_provider, SCHEMA = engine_provider, schema

def get_engine():
    if _engine_provider is None:
        raise RuntimeError("Configurar conexión SIIR antes de cargar datos")
    return _engine_provider()

MASA_VER_TABLE = 'Datos_conciliados_of_ver'
CASOS_TABLE = 'casos_balance'
MASA_TABLE = 'Datos_conciliados_of'
SHIFT1_START, SHIFT1_END = (8, 20)
PAD_SULFUROS = 2
PAD_OXIDOS = 1
PADS = (PAD_SULFUROS, PAD_OXIDOS)
MATERIAL_PAD = {PAD_SULFUROS: 'sulfuros', PAD_OXIDOS: 'oxidos'}

def _window(col, fecha_min, fecha_max):
    w = []
    if fecha_min is not None:
        w.append(f"{col} >= '{pd.Timestamp(fecha_min):%Y-%m-%d}'")
    if fecha_max is not None:
        w.append(f"{col} < '{pd.Timestamp(fecha_max) + pd.Timedelta(days=1):%Y-%m-%d}'")
    return ' WHERE ' + ' AND '.join(w) if w else ''

def _and_window(col, fecha_min, fecha_max):
    """Igual que _window pero para pegar tras un WHERE que ya existe."""
    return _window(col, fecha_min, fecha_max).replace(' WHERE ', ' AND ', 1)

def load_apilado(fecha_min=None, fecha_max=None, engine=None):
    """control_apilado_diario -> mismas columnas que engine.load_apilado()."""
    sql = f"\n    SELECT id, [campaña] AS campana, modulo,\n           volumen_total_estimado_m3            AS vol_total_est,\n           volumen_diario_m3                    AS vol_diario,\n           volumen_acumulado_final_apilado_m3   AS vol_acum_final,\n           avance_porcentaje                    AS avance,\n           altura_promedio_m                    AS altura_prom,\n           promedio_grado                       AS grado_prom,\n           fecha, pad_id, modulo_id, [campaña_id] AS campana_id\n    FROM {SCHEMA}.control_apilado_diario\n    {_window('fecha', fecha_min, fecha_max)}\n    "
    df = pd.read_sql(sql, engine or get_engine())
    df['fecha'] = pd.to_datetime(df['fecha']).dt.normalize()
    for c in ('pad_id', 'campana', 'modulo'):
        df[c] = df[c].astype('int64')
    return df

def _tick_window(fecha_min=None, fecha_max=None):
    """Ventana de ticks [primer día 08:00, día posterior al último 08:00)."""
    clauses = []
    if fecha_min is not None:
        inicio = pd.Timestamp(fecha_min).normalize() + pd.Timedelta(hours=SHIFT1_START)
        clauses.append(f"fecha >= '{inicio:%Y-%m-%dT%H:%M:%S}'")
    if fecha_max is not None:
        fin = pd.Timestamp(fecha_max).normalize() + pd.Timedelta(days=1, hours=SHIFT1_START)
        clauses.append(f"fecha < '{fin:%Y-%m-%dT%H:%M:%S}'")
    return 'WHERE ' + ' AND '.join(clauses) if clauses else ''

def preparar_frontera(out):
    """Reparte el total publicado con proporciones válidas de sus turnos.

    Si el publicador no cierra exactamente, conserva TMS y etiqueta el corte
    normalizado como estimado. Un turno detenido conserva frontera 0 o 1.
    """
    out = out.copy()
    total_turnos = out['TMS_T1'] + out['TMS_T2']
    validos = out[['TMS_T1', 'TMS_T2']].notna().all(axis=1) & out[['TMS_T1', 'TMS_T2']].ge(0).all(axis=1) & total_turnos.gt(0) & out['TMS'].gt(0)
    from .umbrales import TOL_CUADRATURA
    cierre = (total_turnos - out['TMS']).abs() <= TOL_CUADRATURA * out['TMS'].abs()
    out['turnos_ok'] = out['TMS_T1'].gt(0) & out['TMS_T2'].gt(0) & validos
    out['boundary'] = (out['TMS_T1'] / total_turnos).where(validos)
    out['boundary_normalizada'] = validos & ~cierre
    return out

def load_masa(fecha_min=None, fecha_max=None, engine=None, caso_id=None):
    """Masa por turno del dia, tal como la cerro el caso de reconciliacion.

    Lee Datos_conciliados_of_ver y nada mas. La fila del dia es la version
    activa y validada (es_activa = 1, estado_validacion = 'VALIDADO') y, si hay
    varias, la de validacion mas reciente — el mismo desempate que usaba
    vw_datos_conciliados_reporte. El dato llega YA reconciliado: no hay ajuste
    que repartir despues.

    Los dias que no pasaron por un caso validado no salen. No se rellenan con
    la tabla base: sin caso no hay masa, y el consumidor tiene que tratarlos
    como dias sin dato (el modulo que cargaba esos dias queda incompleto).

    Devuelve una fila por dia con:
        TMS        masa seca del dia (turno A + turno B)
        TMS_T1     turno A (08:00-20:00)
        TMS_T2     turno B (20:00-08:00)
        boundary   TMS_T1 / (TMS_T1 + TMS_T2), frontera proporcional entre turnos
                   0.5 fijo de engine.SHIFT1_FRAC
        TMH        masa humeda del dia, medida (Apilado_TMH_promedio_dia, que
                   pese al nombre es la SUMA de los dos turnos, no el promedio)
        TMH_T1/T2  masa humeda por turno
        humedad    humedad del dia en fraccion (Humedad_promedio_dia / 100)
        sal        sal del dia, t. Va dentro del TMH pero no lleva agua
        H_op       horas de apilado efectivo del dia: calendario con al menos
                   una torre entregando
        H_torres   suma de horas por torre; > H_op porque T1, T2 y SRR apilan
                   en paralelo. Diagnostico, no entra en la tasa
        H_op_src   'torre', o 'n/d' si el dia no tiene ticks
        oficial    True siempre: si el dia esta, viene de un caso validado
        fuente_masa 'OFICIAL', la unica etiqueta posible ahora
        caso_id    caso de reconciliacion del que salio la fila. -1 es la carga
                   inicial (sin caso real)
        caso       nombre del caso en casos_balance

    H_op sale de v_ticks_efectivos_torre_10s, que marca cada 10 s si la torre
    esta entregando. Las que apilan son T1, T2 y SRR. H_op es la UNION de las
    tres — horas de calendario en que se apilo — porque la duracion del Gantt
    corre en calendario y las torres trabajan en paralelo; sumarlas contaria
    dos veces la misma hora del dia.

    No confundir con dos horometros que NO son de apilado:
      - reclamo.rotopala_horas_turno: la rotopala es del circuito de RECLAMO,
        aguas abajo. Otra maquina.
      - rc_001/rc_002 de vista_resumen_datos_filtrados: los dos chancadores,
        aguas arriba, y ademas topados en 24 h.
    Con horas de torre el horometro sigue a la masa: el 2026-07-14 se apilaron
    91.9 kt en 23.4 h de torre, mientras la rotopala marcaba 1 h y el
    chancador 24 h. Entre el 07-15 y el 07-19 la rotopala marca 0 h contra
    73-85 kt diarios; las torres dan 22-23 h.

    Sin corrimiento de fecha: 'Fecha' del reporte ya es el dia operacional
    08:00-08:00, igual que 'fecha' en control_apilado_diario.
    """
    eng = engine or get_engine()
    # En modo Caso conservar publicaciones históricas validadas, aunque otro
    # Caso haya sustituido la versión activa. Nunca mezclar IDs por fecha.
    case_clause = ('es_activa = 1' if caso_id is None else
                   'caso_id = :caso_id AND origen = \'AJUSTE_REPORTE\'')
    params = None if caso_id is None else {'caso_id': int(caso_id)}
    case_name = 'k.nombre_caso' if caso_id is None else 'CAST(NULL AS NVARCHAR(255))'
    case_join = f'LEFT JOIN {SCHEMA}.{CASOS_TABLE} k ON k.caso_id = m.caso_id' if caso_id is None else ''
    tms = pd.read_sql(text(f"\n    WITH v AS (\n        SELECT *, ROW_NUMBER() OVER (PARTITION BY Fecha\n                   ORDER BY COALESCE(fecha_validacion, '19000101') DESC,\n                            COALESCE(validation_id, 0) DESC) AS rn\n        FROM {SCHEMA}.{MASA_VER_TABLE}\n        WHERE {case_clause}\n          AND COALESCE(estado_validacion, 'VALIDADO') = 'VALIDADO'\n          AND Apilado_TMS_Real IS NOT NULL\n          AND Apilado_TMH_promedio_dia IS NOT NULL\n          {_and_window('Fecha', fecha_min, fecha_max)}\n    )\n    SELECT CAST(m.Fecha AS DATE) AS fecha,\n           (m.Apilado_TMH_turno_A + COALESCE(m.Sal_turno_A, 0))\n               * (1 - m.Humedad_Turno_A / 100.0) - COALESCE(m.Sal_turno_A, 0) AS TMS_T1,\n           (m.Apilado_TMH_turno_B + COALESCE(m.Sal_Turno_B, 0))\n               * (1 - m.Humedad_Turno_B / 100.0) - COALESCE(m.Sal_Turno_B, 0) AS TMS_T2,\n           m.Apilado_TMS_Real         AS TMS,\n           m.Apilado_TMH_turno_A      AS TMH_T1,\n           m.Apilado_TMH_turno_B      AS TMH_T2,\n           m.Apilado_TMH_promedio_dia AS TMH,\n           m.Humedad_promedio_dia / 100.0 AS humedad,\n           m.Sal_promedio_dia         AS sal,\n           m.caso_id                  AS caso_id,\n           CAST(m.run_id AS VARCHAR(36)) AS reporte_run_id,\n           {case_name}              AS caso\n    FROM v m\n    {case_join}\n    WHERE m.rn = 1\n    "), eng, params=params)
    tms['oficial'] = True
    tms['fuente_masa'] = 'OFICIAL'
    tms['caso_id'] = tms['caso_id'].astype('Int64')
    tms['fecha'] = pd.to_datetime(tms['fecha']).dt.normalize()
    tor = pd.read_sql(f'\n    WITH t AS (\n        SELECT fecha,\n               MAX(CAST(tick_efectivo AS INT)) AS any_on,\n               SUM(CAST(tick_efectivo AS INT)) AS n_on\n        FROM {SCHEMA}.v_ticks_efectivos_torre_10s\n        {_tick_window(fecha_min, fecha_max)}\n        GROUP BY fecha\n    ), d AS (\n        SELECT CAST(DATEADD(hour, -8, fecha) AS DATE) AS fecha,\n               any_on, n_on,\n               CASE WHEN DATEPART(hour, fecha) >= {SHIFT1_START}\n                     AND DATEPART(hour, fecha) <  {SHIFT1_END}\n                    THEN 1 ELSE 2 END AS turno\n        FROM t\n    )\n    SELECT fecha,\n           SUM(any_on) * 10.0 / 3600 AS H_op,\n           SUM(n_on)   * 10.0 / 3600 AS H_torres,\n           SUM(CASE WHEN turno = 1 THEN any_on ELSE 0 END) * 10.0 / 3600 AS H_op_T1,\n           SUM(CASE WHEN turno = 2 THEN any_on ELSE 0 END) * 10.0 / 3600 AS H_op_T2\n    FROM d\n    GROUP BY fecha\n    ', eng)
    tor['fecha'] = pd.to_datetime(tor['fecha']).dt.normalize()
    if fecha_min is not None:
        tor = tor[tor['fecha'] >= pd.Timestamp(fecha_min)]
    if fecha_max is not None:
        tor = tor[tor['fecha'] <= pd.Timestamp(fecha_max)]
    out = tms.merge(tor, on='fecha', how='left')
    out['H_op_src'] = np.where(out['H_op'].notna(), 'torre', 'n/d')
    out = preparar_frontera(out)
    out['boundary_h'] = (out['H_op_T1'] / out['H_op']).where(out['H_op'] > 0)
    return out[['fecha', 'TMS', 'TMS_T1', 'TMS_T2', 'TMH', 'TMH_T1', 'TMH_T2', 'humedad', 'sal', 'H_op', 'H_torres', 'H_op_T1', 'H_op_T2', 'H_op_src', 'turnos_ok', 'boundary', 'boundary_normalizada', 'boundary_h', 'oficial', 'fuente_masa', 'caso_id', 'caso', 'reporte_run_id']]

def coverage(engine=None):
    """Ventana con datos en cada fuente, para intersectarlas.

    La ventana de masa son los extremos de la versionada. Ojo: entre esos dos
    extremos hay dias sin caso y por lo tanto sin masa — hoy, todo diciembre de
    2025 a julio de 2026. La cobertura marca el borde, no la continuidad.
    """
    eng = engine or get_engine()
    a = pd.read_sql(f'SELECT MIN(fecha) f0, MAX(fecha) f1 FROM {SCHEMA}.control_apilado_diario', eng).iloc[0]
    t = pd.read_sql(f"SELECT MIN(Fecha) f0, MAX(Fecha) f1 FROM {SCHEMA}.{MASA_VER_TABLE} WHERE es_activa = 1   AND COALESCE(estado_validacion, 'VALIDADO') = 'VALIDADO'   AND Apilado_TMS_Real IS NOT NULL   AND Apilado_TMH_promedio_dia IS NOT NULL", eng).iloc[0]
    return {'apilado': (pd.Timestamp(a.f0).normalize(), pd.Timestamp(a.f1).normalize()), 'tms': (pd.Timestamp(t.f0).normalize(), pd.Timestamp(t.f1).normalize())}

def casos(engine=None):
    """Casos que publicaron masa, del mas nuevo al mas viejo.

    La ventana sale de los dias que el caso tiene EN LA VERSIONADA, no de
    casos_balance: lo que importa es que dias quedaron publicados con ese caso,
    que es exactamente lo que el informe puede reconstruir. De casos_balance se
    toma solo el nombre.

    Columnas: caso_id, caso, fecha_ini, fecha_fin, n_dias, dias_masa. n_dias es
    el largo calendario de la ventana publicada y dias_masa los dias con fila;
    si difieren, el caso tiene huecos adentro.
    """
    eng = engine or get_engine()
    df = pd.read_sql(f"\n    WITH v AS (\n        SELECT CAST(Fecha AS DATE) AS fecha, caso_id,\n               ROW_NUMBER() OVER (PARTITION BY Fecha\n                   ORDER BY COALESCE(fecha_validacion, '19000101') DESC,\n                            COALESCE(validation_id, 0) DESC) AS rn\n        FROM {SCHEMA}.{MASA_VER_TABLE}\n        WHERE es_activa = 1\n          AND COALESCE(estado_validacion, 'VALIDADO') = 'VALIDADO'\n          AND Apilado_TMS_Real IS NOT NULL\n    )\n    SELECT v.caso_id, k.nombre_caso AS caso,\n           MIN(v.fecha) AS fecha_ini, MAX(v.fecha) AS fecha_fin,\n           COUNT(*) AS dias_masa\n    FROM v LEFT JOIN {SCHEMA}.{CASOS_TABLE} k ON k.caso_id = v.caso_id\n    WHERE v.rn = 1 AND v.caso_id > 0\n    GROUP BY v.caso_id, k.nombre_caso\n    ", eng)
    for c in ('fecha_ini', 'fecha_fin'):
        df[c] = pd.to_datetime(df[c]).dt.normalize()
    df['n_dias'] = (df['fecha_fin'] - df['fecha_ini']).dt.days + 1
    df['caso'] = df['caso'].fillna('(sin nombre en casos_balance)')
    return df.sort_values(['fecha_ini', 'caso_id'], ascending=False).reset_index(drop=True)

def ventana_caso(caso_id, engine=None):
    """caso_id -> caso_id, caso, fecha_ini, fecha_fin, n_dias, dias_masa.

    Levanta ValueError si el caso no publico ningun dia en la versionada: sin
    dias publicados no hay masa que informar.
    """
    k = casos(engine)
    k = k[k['caso_id'] == int(caso_id)]
    if not len(k):
        raise ValueError(f'el caso {caso_id} no tiene dias publicados en {MASA_VER_TABLE}')
    return k.iloc[0]

def caso_oficial(fecha_min=None, fecha_max=None, engine=None):
    """fecha -> caso_id publicado para ese dia. caso_id = -1 queda fuera."""
    eng = engine or get_engine()
    df = pd.read_sql(f"\n    WITH v AS (\n        SELECT CAST(Fecha AS DATE) AS fecha, caso_id,\n               ROW_NUMBER() OVER (PARTITION BY Fecha\n                   ORDER BY COALESCE(fecha_validacion, '19000101') DESC,\n                            COALESCE(validation_id, 0) DESC) AS rn\n        FROM {SCHEMA}.{MASA_VER_TABLE}\n        WHERE es_activa = 1\n          AND COALESCE(estado_validacion, 'VALIDADO') = 'VALIDADO'\n    )\n    SELECT fecha, caso_id FROM v WHERE rn = 1 AND caso_id > 0\n    ", eng)
    df['fecha'] = pd.to_datetime(df['fecha']).dt.normalize()
    if fecha_min is not None:
        df = df[df['fecha'] >= pd.Timestamp(fecha_min)]
    if fecha_max is not None:
        df = df[df['fecha'] <= pd.Timestamp(fecha_max)]
    return df.set_index('fecha')['caso_id']

def pesos_pad(fechas, engine=None):
    """fecha, pad_id, peso — como se reparte el TMS del dia entre los dos pads.

    La tabla de masa trae un TMS por dia y nada mas, asi que el unico dato
    diario que separa oxidos de sulfuros es el volumen apilado de
    control_apilado_diario: el peso de cada pad es su parte del volumen del dia.

    Un dia sin volumen registrado no se puede repartir con su propio dato y cae
    a la mezcla de volumen de toda la ventana pedida; si no hay volumen en
    ninguna parte de la ventana, queda entero en el pad de sulfuros, que es el
    que apila casi siempre.
    """
    fechas = pd.to_datetime(pd.Series(sorted(set(pd.to_datetime(fechas)))))
    if not len(fechas):
        return pd.DataFrame(columns=['fecha', 'pad_id', 'peso'])
    ap = load_apilado(fechas.min(), fechas.max(), engine)
    ap = ap[ap['pad_id'].isin(PADS) & (ap['vol_diario'] > 0)]
    vol = ap.groupby(['fecha', 'pad_id'], as_index=False)['vol_diario'].sum()
    d = pd.DataFrame({'fecha': fechas}).merge(vol, on='fecha', how='left')
    con_vol = d[d['pad_id'].notna()].copy()
    con_vol['peso'] = con_vol['vol_diario'] / con_vol.groupby('fecha')['vol_diario'].transform('sum')
    sin_vol = d.loc[d['pad_id'].isna(), ['fecha']]
    if not len(sin_vol):
        return con_vol[['fecha', 'pad_id', 'peso']].reset_index(drop=True)
    mezcla = con_vol.groupby('pad_id', as_index=False)['vol_diario'].sum()
    if len(mezcla):
        mezcla['peso'] = mezcla['vol_diario'] / mezcla['vol_diario'].sum()
    else:
        mezcla = pd.DataFrame({'pad_id': [PAD_SULFUROS], 'peso': [1.0]})
    sin_vol = sin_vol.merge(mezcla[['pad_id', 'peso']], how='cross')
    out = pd.concat([con_vol[['fecha', 'pad_id', 'peso']], sin_vol], ignore_index=True)
    out['pad_id'] = out['pad_id'].astype('int64')
    return out.sort_values(['fecha', 'pad_id']).reset_index(drop=True)

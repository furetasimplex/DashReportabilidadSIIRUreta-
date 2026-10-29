"""Lecturas acotadas de insumos para el informe de módulos; sin escrituras."""
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from sqlalchemy import text

from . import db_source as dbs


def cargar_fuentes(engine, fecha_min, fecha_max):
    """Rango operacional inclusivo. Cada fuente fallida conserva ausencia visible."""
    start = pd.Timestamp(fecha_min).normalize()
    end = pd.Timestamp(fecha_max).normalize() + pd.Timedelta(days=1)
    if pd.isna(start) or pd.isna(end) or start >= end:
        raise ValueError('Rango inválido para fuentes del informe.')
    params = {'desde': start.date(), 'hasta': end.date()}
    schema = dbs.SCHEMA  # Configuración SIIR de la aplicación, no entrada del navegador.
    queries = {
        'movcam': f'''SELECT * FROM {schema}.mov_cam
            WHERE Fecha >= :desde AND Fecha < :hasta AND Destino = 'CH01'
            ORDER BY Fecha, Turno, mov_id''',
        'srr': f'''SELECT Fecha, Turno, SRR_TMS_Turno, CuT_SRR, CuS_SRR,
                ClayBeta_SRR, Malla100_SRR, CO3_SRR, Recuperacion_SRR
            FROM {schema}.fn_reconstitucion_srr_turno_emision_test(:desde, :hasta)''',
        'datos_turno': f'''SELECT * FROM {schema}.Datos_conciliados_of
            WHERE Fecha >= :desde AND Fecha < :hasta ORDER BY Fecha''',
    }

    def read(key):
        try:
            return key, pd.read_sql(text(queries[key]), engine, params=params), None
        except Exception:
            # No mostrar mensajes ODBC/conexión con detalles de infraestructura.
            return key, pd.DataFrame(), f'No se pudo consultar {key}; sus atributos quedan sin dato.'

    result = {'warnings': []}
    # Engine abre una conexión por lectura; no se comparte una Connection entre hilos.
    with ThreadPoolExecutor(max_workers=len(queries)) as pool:
        for key, frame, warning in pool.map(read, queries):
            result[key] = frame
            if warning:
                result['warnings'].append(warning)
    return result


def cargar_reposo(engine, pad, claves):
    """Hito real de los módulos seleccionados; no inferirlo del fin de carguío."""
    claves = sorted({(int(c), int(m)) for c, m in claves})
    if not claves:
        return pd.DataFrame(), []
    params = {'pad': int(pad)}
    clauses = []
    for i, (campaign, module) in enumerate(claves):
        params[f'c{i}'], params[f'm{i}'] = campaign, module
        clauses.append(f'(TRY_CONVERT(int, numero_campana)=:c{i} AND TRY_CONVERT(int, nombre_modulo)=:m{i})')
    sql = f'''SELECT numero_campana, nombre_modulo, fecha_ini_reposo
        FROM {dbs.SCHEMA}.campana_parcela_control
        WHERE pad_id=:pad AND ({' OR '.join(clauses)})'''
    try:
        return pd.read_sql(text(sql), engine, params=params), []
    except Exception:
        return pd.DataFrame(), ['No se pudo consultar control de reposo; su fecha queda sin dato.']

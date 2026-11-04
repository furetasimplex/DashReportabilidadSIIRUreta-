"""Extraccion de los datos de un Caso a un Excel, y su lectura de vuelta (sin SQL).

El script `scripts/extraer_datos_caso.py` consulta la base (solo SELECT) y entrega aqui
lo leido; este modulo lo ordena en hojas en formato largo y puede reconstruirlo. Asi el
Caso se puede probar en otro entorno sin acceso a la base. El archivo no contiene
credenciales ni cadenas de conexion.
"""
from __future__ import annotations

import pandas as pd

SHEETS = ('caso', 'flujos_run', 'riego', 'cu_riego', 'cu_drena', 'recuperaciones_pad', 'campana',
          'primer_riego', 'apilado', 'perfil_guardado', 'historico_oficial', 'resumen')
_PAD_ID = {'OXIDOS': 1, 'SULFUROS': 2}


def _long_wide(frame, pad, value_name):
    if frame is None or len(frame) == 0:
        return pd.DataFrame(columns=['pad', 'pila', 'fecha', value_name])
    out = frame.copy()
    out.index = pd.to_datetime(out.index).normalize()
    out = out.rename_axis('fecha').reset_index().melt(id_vars='fecha', var_name='pila', value_name=value_name)
    out = out.dropna(subset=[value_name])
    out.insert(0, 'pad', pad)
    return out[['pad', 'pila', 'fecha', value_name]].sort_values(['pila', 'fecha']).reset_index(drop=True)


def build_tables(case, window, flows, series, recoveries, wip, first_irrigation, stacking,
                 saved_profile, history, notes=()):
    """Arma las hojas.

    case: dict con id, nombre, run_id, fecha_inicio, fecha_fin, modelo_codigo, modelo_version, total_flujos.
    window: (inicio, fin) del Caso.   flows: filas (codigo_flujo, masa_medida, masa_reconciliada,
    fino_cu_medido, fino_cu_reconciliado) del run.   series: {pad: {'riego': DataFrame ancho,
    'cu_riego': Serie, 'cu_drena': DataFrame ancho}} SIN relleno.   recoveries: filas
    (PAD, Parcela, Campana, Fecha_drenaje, Recuperacion_parcela).   wip: {pad: {pila: dict}}.
    first_irrigation: {pad: {pila: fecha}}.   stacking: {(pad_id, parcela): dict}.
    saved_profile: {(pila, 'YYYY-MM-DD'): q_pls}.   history: filas dict del historico oficial.
    """
    ws, we = (pd.Timestamp(window[0]).normalize(), pd.Timestamp(window[1]).normalize())
    tables = {}
    tables['caso'] = pd.DataFrame(
        [dict(campo=k, valor=str(v)[:10] if k in ('fecha_inicio', 'fecha_fin') else v)
         for k, v in dict(case, ventana_inicio=ws.date().isoformat(), ventana_fin=we.date().isoformat()).items()])
    tables['flujos_run'] = pd.DataFrame(
        [tuple(r) for r in flows],
        columns=['codigo_flujo', 'masa_medida', 'masa_reconciliada', 'fino_cu_medido', 'fino_cu_reconciliado'])
    tables['riego'] = pd.concat([_long_wide(s.get('riego'), pad, 'caudal_m3h') for pad, s in series.items()], ignore_index=True)
    cu_riego = []
    for pad, s in series.items():
        serie = s.get('cu_riego')
        if serie is not None and len(serie):
            frame = serie.dropna().rename('cu_gL').rename_axis('fecha').reset_index()
            frame['fecha'] = pd.to_datetime(frame['fecha']).dt.normalize()
            frame.insert(0, 'pad', pad)
            cu_riego.append(frame)
    tables['cu_riego'] = (pd.concat(cu_riego, ignore_index=True) if cu_riego
                          else pd.DataFrame(columns=['pad', 'fecha', 'cu_gL']))
    tables['cu_drena'] = pd.concat([_long_wide(s.get('cu_drena'), pad, 'cu_gL') for pad, s in series.items()], ignore_index=True)
    tables['recuperaciones_pad'] = pd.DataFrame(
        [tuple(r) for r in recoveries], columns=['PAD', 'Parcela', 'Campana', 'Fecha_drenaje', 'Recuperacion_parcela'])
    tables['recuperaciones_pad']['Fecha_drenaje'] = pd.to_datetime(tables['recuperaciones_pad']['Fecha_drenaje']).dt.normalize()
    rows = []
    for pad, piles in wip.items():
        for pila, info in piles.items():
            rows.append(dict(pad=pad, pila=pila, ini_aporte=info.get('ini_aporte'), fin_ciclo=info.get('fin_ciclo'),
                             CuTf_t=info.get('CuTf'), sin_campana=bool(info.get('sin_campana'))))
    tables['campana'] = pd.DataFrame(rows, columns=['pad', 'pila', 'ini_aporte', 'fin_ciclo', 'CuTf_t', 'sin_campana'])
    tables['primer_riego'] = pd.DataFrame(
        [dict(pad=pad, pila=pila, primer_riego=pd.Timestamp(day).normalize())
         for pad, piles in first_irrigation.items() for pila, day in piles.items()],
        columns=['pad', 'pila', 'primer_riego'])
    names = {v: k for k, v in _PAD_ID.items()}
    tables['apilado'] = pd.DataFrame(
        [dict(pad=names.get(pad_id, pad_id), pila=f'P{parcela:02d}', campana=info['camp'], inicio=info['f0'],
              fin=info['f1'], cu_fino_t=info['fin'], tms=info['tms'], ley_pct=info['ley'])
         for (pad_id, parcela), info in stacking.items()],
        columns=['pad', 'pila', 'campana', 'inicio', 'fin', 'cu_fino_t', 'tms', 'ley_pct'])
    tables['perfil_guardado'] = pd.DataFrame(
        [dict(pila=pila, fecha=day, q_pls_m3h=q) for (pila, day), q in sorted(saved_profile.items())],
        columns=['pila', 'fecha', 'q_pls_m3h'])
    keep = ['date', 'label', 'parcela', 'caso_id', 'run_id', 'fdrena', 'q', 'q_pls', 'cu_riego', 'cu_drena']
    tables['historico_oficial'] = pd.DataFrame([{k: r.get(k) for k in keep} for r in history], columns=keep)
    tables['historico_oficial']['date'] = pd.to_datetime(tables['historico_oficial']['date']).dt.normalize()
    summary = [dict(hoja=name, filas=len(tables[name])) for name in tables]
    summary += [dict(hoja='nota', filas=0, detalle=n) for n in notes]
    tables['resumen'] = pd.DataFrame(summary)
    return {name: tables[name] for name in SHEETS}


def write_workbook(tables, path):
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        for name, frame in tables.items():
            frame.to_excel(writer, sheet_name=name, index=False)
            sheet = writer.sheets[name]
            for column in sheet.columns:
                width = max((len(str(c.value)) for c in column[:200] if c.value is not None), default=8)
                sheet.column_dimensions[column[0].column_letter].width = min(max(width + 2, 10), 48)
    return path


def read_workbook(path):
    """Reconstruye lo entregado a `build_tables` desde el Excel (sin SQL)."""
    sheets = pd.read_excel(path, sheet_name=None)
    missing = [name for name in SHEETS if name not in sheets]
    if missing:
        raise ValueError('el Excel no tiene las hojas: ' + ', '.join(missing))
    case = {row.campo: row.valor for row in sheets['caso'].itertuples()}
    series = {}
    for pad in sorted(set(sheets['riego']['pad']) | set(sheets['cu_riego']['pad'])):
        riego = sheets['riego'][sheets['riego']['pad'] == pad]
        cu_r = sheets['cu_riego'][sheets['cu_riego']['pad'] == pad]
        cu_d = sheets['cu_drena'][sheets['cu_drena']['pad'] == pad]
        series[pad] = dict(
            riego=riego.pivot_table(index='fecha', columns='pila', values='caudal_m3h', aggfunc='first').sort_index().astype(float),
            cu_riego=pd.Series(cu_r['cu_gL'].to_numpy(dtype=float), index=pd.DatetimeIndex(cu_r['fecha']), name='cu_riego').sort_index(),
            cu_drena=cu_d.pivot_table(index='fecha', columns='pila', values='cu_gL', aggfunc='first').sort_index().astype(float))
    wip = {}
    for row in sheets['campana'].itertuples():
        wip.setdefault(row.pad, {})[row.pila] = dict(
            ini_aporte=row.ini_aporte, fin_ciclo=row.fin_ciclo, CuTf=row.CuTf_t, sin_campana=bool(row.sin_campana))
    first = {}
    for row in sheets['primer_riego'].itertuples():
        first.setdefault(row.pad, {})[row.pila] = pd.Timestamp(row.primer_riego)
    curves = {}
    for pad, group in sheets['recuperaciones_pad'].groupby('PAD'):
        for parcela, g in group.groupby('Parcela'):
            g = g.sort_values('Fecha_drenaje')
            curves.setdefault(pad, {})[int(parcela)] = dict(
                dates=[d.date() for d in pd.to_datetime(g['Fecha_drenaje'])], values=[float(v) for v in g['Recuperacion_parcela']])
    saved = {(row.pila, pd.Timestamp(row.fecha).date().isoformat()): float(row.q_pls_m3h)
             for row in sheets['perfil_guardado'].itertuples()}
    return dict(case=case, flows=sheets['flujos_run'], series=series, wip=wip, first_irrigation=first, curves=curves,
                stacking=sheets['apilado'], saved_profile=saved, history=sheets['historico_oficial'],
                recoveries=sheets['recuperaciones_pad'], summary=sheets['resumen'])

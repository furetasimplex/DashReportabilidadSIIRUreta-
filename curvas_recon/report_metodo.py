# -*- coding: utf-8 -*-
"""Reporte de recuperaciones POR EL METODO RECONCILIADO.

Es el mismo libro `Reporte_Recuperaciones_Metodo_Reconciliado.xlsx` que armaba
el pipeline (`pipeline/p0_motor.py` + `pipeline/p4_reporte_xlsx.py`), pero acá
va como funciones importables para que el boton 'Generar reporte' del dashboard
produzca EXACTAMENTE ese libro con la corrida que se acaba de reconciliar. Los
dos scripts del pipeline ahora llaman a este modulo, asi que hay una sola
implementacion.

Dos pasos:

  `construir_doc(runs, ...)`  corridas del motor -> dict de curvas por pila
                              (el mismo `motor_curvas.json`).
  `escribir_libro(doc, out)`  ese dict -> el .xlsx con las hojas de datos por
                              pad y sus dos hojas de graficos.

`runs` es {caso_id: {'ws', 'we', 'caso', 'pads': {label: {'res': res}}}}, donde
`res` es lo que devuelve `recon_engine.reconcile_flowsheet`. Cada dia pertenece
a un solo caso, asi que las ventanas que se pisan no cuentan dos veces.
"""
import os

import numpy as np
import pandas as pd
from openpyxl.chart import LineChart, Reference, Series
from openpyxl.chart.marker import Marker
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Alignment

from . import recon_engine as E
from .db_pipeline import connect, SCHEMA
from sqlalchemy import text

RAIZ = os.path.dirname(os.path.abspath(__file__))

K_F = 0.024
PAD_ID = {'OXIDOS': 1, 'SULFUROS': 2}
NPILAS = {'OXIDOS': 32, 'SULFUROS': 28}
XL_PLANTA = os.getenv('RECON_PLANTA_XLSX', os.path.join(RAIZ, 'Reporte_Recuperaciones 31 de Julio 2026.xlsx'))
CORTE_PLANTA = pd.Timestamp('2026-07-31')
BUSCA_RIEGO_DESDE = pd.Timestamp('2024-06-01')

# el libro de planta: sulfuros va P21..P28, P1..P20; oxidos va P1..P32
ORDEN = {'OXIDOS': list(range(1, 33)),
         'SULFUROS': list(range(21, 29)) + list(range(1, 21))}
HOJA = {'OXIDOS': 'Rec Ox', 'SULFUROS': 'Rec Sulfuro'}
HDR = ['campana', 'ciclos', 'rec_max', 'aporte', 'apilado', 'rec_termino',
       'recuperable', 'wip']


def net_recovery_increment(q_m3h, cu_drena_gl, cu_riego_gl,
                           fdrena=None, missing=None):
    """Daily net Cu recovery (t Cu) under the report's existing equation.

    ``None`` means a required operational input is missing; explicit zero flow
    is a known zero increment. Outside an anchored case, callers pass
    ``E.FDRENA_MAX`` and the result is a proxy, not directly measured recovery.
    """
    try:
        q = float(q_m3h)
    except (TypeError, ValueError):
        return missing
    if not np.isfinite(q) or q < 0:
        return missing
    if q == 0:
        return 0.0
    try:
        cd, cr = float(cu_drena_gl), float(cu_riego_gl)
    except (TypeError, ValueError):
        return missing
    if not np.isfinite(cd) or not np.isfinite(cr):
        return missing
    factor = E.FDRENA_MAX if fdrena is None else float(fdrena)
    if not np.isfinite(factor):
        return missing
    return (factor * q * cd - q * cr) * K_F


def historical_net_increment(q_m3h, cu_drena_gl, cu_riego_gl):
    """Vectorized report-compatible baseline increment, retaining NaN gaps."""
    q = np.asarray(q_m3h, dtype=float)
    cd = np.asarray(cu_drena_gl, dtype=float)
    cr = np.asarray(cu_riego_gl, dtype=float)
    valid = np.isfinite(q) & (q >= 0)
    valid &= (q == 0) | (np.isfinite(cd) & np.isfinite(cr))
    result = np.full(np.broadcast(q, cd, cr).shape, np.nan, dtype=float)
    zero = valid & (q == 0)
    wet = valid & (q > 0)
    result[zero] = 0.0
    result[wet] = (E.FDRENA_MAX * q[wet] * cd[wet] - q[wet] * cr[wet]) * K_F
    return result


# ── paso 1: curvas por pila ─────────────────────────────────────────────────

def inicio_ciclo(serie, f0, f1):
    """Primer dia del ciclo de riego de una campana.

    Base: el primer dia con riego > 0 desde que TERMINA el apilado (`f1`).
    Pero varias pilas se empiezan a regar por modulos mientras todavia se
    apilan, y la planta cuenta esa produccion. Entonces, si ese dia viene
    pegado a una corrida de riego que arranco antes, el ciclo se estira hacia
    atras hasta el comienzo de la corrida, sin pasar del inicio del apilado
    (`f0`).
    """
    s = serie[serie.index >= f1]
    s = s[s > 0]
    if not len(s):
        return None
    d0 = pd.Timestamp(s.index[0]).normalize()
    idx = serie.index
    i = idx.get_indexer([d0])[0]
    while i > 0 and idx[i - 1] >= f0:
        v = serie.iloc[i - 1]
        if not (v > 0):
            break
        i -= 1
    return pd.Timestamp(idx[i]).normalize()


def leer_planta(label, xl=XL_PLANTA):
    """Cabecera y curva de planta, conservando los huecos del eje de días.

    Ox numera las parcelas en fila 9; Sulfuro en fila 10. Se identifica la
    parcela por esa fila, no por su posición entre las columnas exportadas.
    """
    if not os.path.exists(xl):
        return {}
    d = pd.read_excel(xl, sheet_name=HOJA[label], header=None)
    out = {}
    legacy_header = isinstance(d.iat[0, 1], str) and d.iat[0, 1].startswith('P') if d.shape[1] > 1 else False
    header_start = 1 if legacy_header else 0
    ids_row = 9 if legacy_header or label == 'SULFUROS' else 8
    if len(d) <= ids_row:
        return out
    for j in range(1, d.shape[1]):
        num = pd.to_numeric(d.iat[ids_row, j], errors='coerce')
        if not np.isfinite(num) or int(num) != num or int(num) not in ORDEN[label]:
            continue
        num = int(num)
        col = pd.to_numeric(d.iloc[:, j], errors='coerce')
        h = {k: (float(col.iloc[header_start + i]) if np.isfinite(col.iloc[header_start + i]) else None)
             for i, k in enumerate(HDR)}
        curve = col.iloc[ids_row + 1:]
        finite = np.flatnonzero(np.isfinite(curve.to_numpy(dtype=float)))
        curve = curve.iloc[:finite[-1] + 1] if len(finite) else curve.iloc[:0]
        h['curva'] = [float(x) if np.isfinite(x) else None for x in curve]
        out[num] = h
    return out


def leer_apilado(asof=None):
    """{(pad_id, parcela): dict(camp, f0, f1, fin, tms, ley)} campana vigente."""
    filtro_fecha = ' AND Fecha < :hasta_exclusivo' if asof is not None else ''
    params = ({'hasta_exclusivo': pd.Timestamp(asof).normalize() + pd.Timedelta(days=1)}
              if asof is not None else {})
    with connect() as cn:
        rows = cn.execute(text(f"""
        WITH x AS (
          SELECT pad_id, Parcela, Campana,
                 MIN(Fecha) f0, MAX(Fecha) f1,
                 SUM(Finos_cut) fin, SUM(TMS) tms,
                 ROW_NUMBER() OVER (PARTITION BY pad_id, Parcela
                                    ORDER BY MAX(Fecha) DESC) rn
          FROM {SCHEMA}.modulos_turnos
          WHERE Parcela IS NOT NULL{filtro_fecha}
          GROUP BY pad_id, Parcela, Campana)
        SELECT pad_id, Parcela, Campana, f0, f1, fin, tms FROM x WHERE rn = 1"""), params).fetchall()
    out = {}
    for pid, par, camp, f0, f1, fin, tms in rows:
        fin, tms = float(fin or 0), float(tms or 0)
        out[(int(pid), int(par))] = dict(
            camp=int(camp), f0=pd.Timestamp(f0), f1=pd.Timestamp(f1),
            fin=fin, tms=tms, ley=(fin / tms * 100 if tms else None))
    return out


def construir_doc(runs, end=None, corte_planta=CORTE_PLANTA, xl=XL_PLANTA,
                  verbose=True):
    """Curvas de recuperacion por pila, medidas y reconciliadas.

    Dentro de las ventanas con ancla de `runs` manda el Q y el Cu que
    reconcilio el motor; fuera de ellas van las leyes medidas de la DB con el
    Fdrenaje base (`FDRENA_MAX`), porque la DB no tiene caudal de drenaje por
    pila. `end` estira las curvas mas alla del ultimo caso (default: el fin
    del caso mas nuevo)."""
    casos = sorted(runs)
    if not casos:
        raise ValueError('construir_doc necesita al menos una corrida')
    fin_casos = max(runs[c]['we'] for c in casos)
    END = pd.Timestamp(end) if end is not None else fin_casos
    END = max(END, fin_casos)
    APIL = leer_apilado(asof=END)

    # cada dia pertenece a un solo caso: sin doble conteo en bordes compartidos
    day_caso = {}
    for cid in casos:
        d, we = runs[cid]['ws'], runs[cid]['we']
        while d <= we:
            day_caso.setdefault(d, cid)
            d += pd.Timedelta(days=1)

    doc = dict(end=str(END.date()), corte_planta=str(pd.Timestamp(corte_planta).date()),
               casos=[dict(id=c, desde=str(runs[c]['ws'].date()),
                           hasta=str(runs[c]['we'].date()),
                           run=runs[c]['caso']['run_id']) for c in casos],
               pads={})

    for label in ('OXIDOS', 'SULFUROS'):
        pid = PAD_ID[label]
        PL = leer_planta(label, xl)

        # solo las pilas vistas en las corridas
        activas = set()
        for cid in casos:
            res = (runs[cid]['pads'].get(label) or {}).get('res')
            if res:
                activas.update(pl['parcela'] for pl in res['piles']
                               if pl.get('label', label) == label)

        # La historia debe alcanzar el inicio real de todas las campañas,
        # incluso si precede el corte histórico usado por el reporte antiguo.
        inicios = [a['f0'] for (pad, num), a in APIL.items()
                   if pad == pid and f'P{num:02d}' in activas and pd.notna(a['f0'])]
        desde_historia = min([BUSCA_RIEGO_DESDE] + inicios)
        r_ini = E.load_riego(label, desde_historia, END)

        info = {}
        for num in range(1, NPILAS[label] + 1):
            if 'P%02d' % num not in activas:
                continue
            a = APIL.get((pid, num))
            p = 'P%02d' % num
            if not a or p not in r_ini.columns:
                continue
            d0 = inicio_ciclo(r_ini[p], a['f0'], a['f1'])
            if d0 is None:
                continue                      # apilada pero aun sin regar
            info[p] = dict(a, ini=d0, num=num)

        if not info:
            continue
        start = min(v['ini'] for v in info.values())

        # Ya se descargó la misma serie histórica para ubicar el arranque.
        # Riego no se imputa entre días: recortar conserva sus valores diarios.
        riego = r_ini.loc[(r_ini.index >= start) & (r_ini.index <= END)].copy()
        cu_riego = E.load_cu_riego(label, start, END)
        drena_cu = E.load_drena_cu(label, start, END)

        # extraccion reconciliada dia a dia, dentro de las ventanas con ancla
        rec_ext = {}
        for cid in casos:
            res = (runs[cid]['pads'].get(label) or {}).get('res')
            if not res:
                continue
            for pl in res['piles']:
                if pl.get('label', label) != label:
                    continue
                for d in pl['daily']:
                    if day_caso.get(d['date']) != cid:
                        continue
                    fp, fr = d['fino_pls_final'], d['fino_riego_final']
                    if fp is None or fr is None:
                        continue
                    rec_ext[(pl['parcela'], d['date'])] = (fp - fr) * K_F

        cal = pd.date_range(start, END, freq='D')
        q_all = riego.reindex(cal).fillna(0.0) if not riego.empty else pd.DataFrame(index=cal)
        cur_all = cu_riego.reindex(cal)
        cpl_all = drena_cu.reindex(cal) if not drena_cu.empty else pd.DataFrame(index=cal)
        pos = {d: i for i, d in enumerate(cal)}
        i_corte = pos.get(pd.Timestamp(corte_planta))

        pilas = []
        for p in sorted(info, key=lambda x: int(x[1:])):
            v = info[p]
            i0 = pos[v['ini']]
            pl = PL.get(v['num'], {})

            q = (q_all[p].to_numpy(dtype=float) if p in q_all.columns
                 else np.zeros(len(cal)))
            q = np.where(q > 0, q, 0.0)
            cu_r = cur_all.to_numpy(dtype=float)
            cu_p = (cpl_all[p].to_numpy(dtype=float) if p in cpl_all.columns
                    else np.full(len(cal), np.nan))

            # fuera de las ventanas con ancla no hay nada que reconciliar:
            # leyes medidas de la DB y el Fdrenaje base del motor (FDRENA_MAX).
            e_med = historical_net_increment(q, cu_p, cu_r)
            # El reporte conserva su acumulación histórica actual: los días
            # sin lecturas no aportan masa. La UI puede conservarlos como gaps.
            e_med = np.nan_to_num(e_med, nan=0.0)
            # dentro de las ventanas manda el Q y el Cu reconciliados del motor
            e_rec = e_med.copy()
            for (pp, dd), val in rec_ext.items():
                if pp == p and dd in pos:
                    e_rec[pos[dd]] = val

            med = np.cumsum(e_med[i0:])
            rec = np.cumsum(e_rec[i0:])
            cov = ((q > 0) & ~np.isnan(cu_p)).astype(int)[i0:]
            rie = (q > 0).astype(int)[i0:]
            vol = float(q[i0:].sum()) * 24.0   # load_riego entrega m3/h
            j = (i_corte - i0) if i_corte is not None else None
            rec_corte = float(rec[j]) if j is not None and 0 <= j < rec.size else None

            # la planta solo es comparable si mira la misma campana
            camp_pl = int(pl['campana']) if pl.get('campana') else None
            misma = (camp_pl == v['camp'])

            pilas.append(dict(
                p=p, num=v['num'], campana=v['camp'],
                ini=str(v['ini'].date()), apilado_ini=str(v['f0'].date()),
                apilado_fin=str(v['f1'].date()), n=int(med.size),
                apilado=round(v['fin'], 3), tms=round(v['tms'], 1),
                ley=(round(v['ley'], 4) if v['ley'] else None),
                vol_riego=round(vol, 1),
                rl=(round(vol / v['tms'], 4) if v['tms'] else None),
                dias_riego=int(rie.sum()), dias_ley=int(cov.sum()),
                t_med=round(float(med[-1]), 3), t_rec=round(float(rec[-1]), 3),
                pct=round(float(rec[-1]) / v['fin'] * 100, 3) if v['fin'] else None,
                rec_corte=(round(rec_corte, 3) if rec_corte is not None else None),
                pct_corte=(round(rec_corte / v['fin'] * 100, 3)
                           if rec_corte is not None and v['fin'] else None),
                planta_ok=bool(misma),
                planta_campana=camp_pl,
                planta_ciclos=(int(pl['ciclos']) if misma and pl.get('ciclos') else None),
                planta_pct=(round(pl['rec_max'], 3) if misma and pl.get('rec_max') else None),
                planta_apilado=(round(pl['apilado'], 3) if misma and pl.get('apilado') else None),
                planta_rec_termino=(round(pl['rec_termino'], 3) if misma and pl.get('rec_termino') else None),
                planta_curva=([round(x, 4) if x is not None else None
                               for x in pl.get('curva', [])] if misma else []),
                med=[round(float(x), 3) for x in med],
                rec=[round(float(x), 3) for x in rec],
                cov=[int(x) for x in cov]))

        doc['pads'][label] = dict(pilas=pilas, desde=str(start.date()))
        if verbose:
            nue = sum(1 for x in pilas if not x['planta_ok'])
            print('%-9s vistas en casos=%2d  con curva=%2d  desde %s  campanas=%s  '
                  'fuera de la hoja=%d' % (label, len(activas), len(pilas),
                                           start.date(),
                                           sorted({x['campana'] for x in pilas}), nue))
    return doc


# ── paso 2: el libro ────────────────────────────────────────────────────────

FILAS = ['Campana', 'Ciclos', 'Recuperacion max.', 'Aporte Parcelas',
         'Apilado tmf', 'Rec termino ciclo', 'Recuperable', 'WIP']
CHART = {'OXIDOS': 'Curvas Ox', 'SULFUROS': 'Curvas Sulfuro'}
COL_T = 40          # bloque de toneladas, lejos a la derecha de los graficos
PROD_SHEET = 'Prod'


def _corte_corto(doc):
    """Encabezado del corte de planta en dd-mm, como el libro original
    ('Recuperacion al 31-07 [%]'). Sale de `doc['corte_planta']`, no hardcodeado."""
    return pd.Timestamp(doc['corte_planta']).strftime('%d-%m')


def hoja_pad(doc, label):
    """Bloque de cabecera + curva acumulada en % por dia de ciclo."""
    P = doc['pads'][label]['pilas']
    nmax = max(q['n'] for q in P)
    cols = [q['p'] for q in P]
    idx = FILAS + [''] + [str(i) for i in range(1, nmax + 1)]
    M = pd.DataFrame(index=idx, columns=cols, dtype=object)
    for q in P:
        c, ap = q['p'], q['apilado']
        rt = q['planta_rec_termino']
        recup = (ap * rt / 100.0) if rt else None
        M.at['Campana', c] = q['campana']
        M.at['Ciclos', c] = q['n']
        M.at['Recuperacion max.', c] = max(q['rec']) * 100.0 / ap if ap and q['rec'] else None
        M.at['Aporte Parcelas', c] = q['t_rec']
        M.at['Apilado tmf', c] = ap
        M.at['Rec termino ciclo', c] = rt
        M.at['Recuperable', c] = (round(recup, 3) if recup else None)
        M.at['WIP', c] = (round(recup - q['t_rec'], 3) if recup else None)
        M.at['', c] = q['num']
        if ap:
            k = 100.0 / ap
            for i, v in enumerate(q['rec'], start=1):
                M.at[str(i), c] = round(v * k, 6)
    return M


def _escribir_hoja_pad(ws, doc, label):
    """Escribe la matriz en el formato de la hoja de recuperaciones de planta."""
    pilas = doc.get('pads', {}).get(label, {}).get('pilas', [])
    pilas = sorted(pilas, key=lambda q: ORDEN[label].index(q['num']))
    etiquetas = ['Campana', 'Ciclos', 'Recuperacion max.', 'Aporte Parcelas',
                 'Apilado tmf', 'Rec termino ciclo', 'Recuperable', 'WIP']
    for row, etiqueta in enumerate(etiquetas, start=1):
        ws.cell(row=row, column=1, value=etiqueta)
    for col, q in enumerate(pilas, start=2):
        ap = q['apilado']
        rt = q['planta_rec_termino']
        recup = ap * rt / 100.0 if rt is not None else None
        aporte = round(q['rec'][-1], 3) if q['rec'] else q['t_rec']
        rec_max = max(q['rec']) * 100.0 / ap if ap and q['rec'] else None
        valores = [q['campana'], q['n'], rec_max, aporte, ap, rt,
                   round(recup, 3) if recup is not None else None,
                   round(recup - aporte, 3) if recup is not None else None]
        for row, value in enumerate(valores, start=1):
            ws.cell(row=row, column=col, value=value)
        if label == 'OXIDOS':
            ws.cell(row=9, column=col, value=q['num'])
        else:
            ws.cell(row=10, column=col, value=q['num'])
        if ap:
            curve_row = 10 if label == 'OXIDOS' else 11
            for i, value in enumerate(q['rec'], start=curve_row):
                ws.cell(row=i, column=col, value=round(value * 100.0 / ap, 6))

    if label == 'OXIDOS':
        for i in range(max((q['n'] for q in pilas), default=0)):
            ws.cell(10 + i, 1, i + 1)
        curve_row = 10
    else:
        ws.cell(row=10, column=1, value='Dias Lix')
        for i in range(max((q['n'] for q in pilas), default=0)):
            ws.cell(11 + i, 1, i + 1)
        curve_row = 11

    ws.column_dimensions['A'].width = 26
    ws.freeze_panes = f'B{curve_row}'
    max_row = max(10, curve_row + max((q['n'] for q in pilas), default=0) - 1)
    for row in ws.iter_rows(min_row=1, max_row=max_row, min_col=1,
                            max_col=max(1, len(pilas) + 1)):
        for cell in row:
            cell.font = Font(name='Arial', size=10)
    for col in range(2, len(pilas) + 2):
        ws.column_dimensions[get_column_letter(col)].width = 11
        ws.cell(1, col).font = Font(name='Arial', size=10, bold=True)
        for row in (1, 2):
            ws.cell(row, col).number_format = '0'
        for row in range(3, 9):
            ws.cell(row, col).number_format = '#,##0.0'
        ws.cell(6, col).fill = PatternFill('solid', fgColor='FFFF00')
        id_row = 9 if label == 'OXIDOS' else 10
        ws.cell(id_row, col).fill = PatternFill('solid', fgColor='FFFF00')
        ws.cell(id_row, col).font = Font(name='Arial', size=10, bold=True)
        for row in range(curve_row, max_row + 1):
            ws.cell(row, col).number_format = '0.00'


def _escribir_prod(w, doc):
    """Hoja ancha con el Cu neto diario reconstruido por pila, no cátodos."""
    pad_defs = [('OXIDOS', 'Óxidos'), ('SULFUROS', 'Sulfuros')]
    active = [(label, title, sorted(doc.get('pads', {}).get(label, {}).get('pilas', []),
                                    key=lambda q: ORDEN[label].index(q['num'])))
              for label, title in pad_defs
              if doc.get('pads', {}).get(label, {}).get('pilas')]
    ws = w.book.create_sheet(PROD_SHEET)

    first_col = 2
    col_by_pad = {}
    all_dates = set()
    for label, title, pilas in active:
        begin = first_col
        col_by_pad[label] = {}
        for q in pilas:
            col_by_pad[label][q['p']] = first_col
            first_col += 1
            start = pd.Timestamp(q.get('ini') or doc['pads'][label].get('desde'))
            all_dates.update(start + pd.Timedelta(days=i) for i in range(len(q['rec'])))
        ws.merge_cells(start_row=3, start_column=begin,
                       end_row=3, end_column=first_col - 1)
        ws.cell(3, begin, title)

    ws['A1'] = 'Cu neto diario reconstruido [t Cu/dia]'
    cases = ', '.join(str(c['id']) for c in doc.get('casos', []))
    ws['A2'] = f'Caso {cases} — corte {doc["end"]}' if cases else f'Corte {doc["end"]}'
    if not all_dates:
        ws['A4'] = 'Parcela'
        ws['A1'].font = Font(name='Arial', size=10, bold=True)
        ws.column_dimensions['A'].width = 46
        return ws

    final_col = first_col - 1
    ws['A4'] = 'Parcela'
    for label, title, pilas in active:
        for q in pilas:
            col = col_by_pad[label][q['p']]
            ws.cell(4, col, q['num'])

    dates = sorted(all_dates)
    row_by_date = {day: row for row, day in enumerate(dates, start=5)}
    for day, row in row_by_date.items():
        ws.cell(row, 1, day.to_pydatetime())
    for label, title, pilas in active:
        for q in pilas:
            col = col_by_pad[label][q['p']]
            start = pd.Timestamp(q.get('ini') or doc['pads'][label].get('desde'))
            previous = 0.0
            for i, cumulative in enumerate(q['rec']):
                day = start + pd.Timedelta(days=i)
                value = float(cumulative) - previous
                ws.cell(row_by_date[day], col, round(value, 3))
                previous = float(cumulative)

    # La fuente y el color de relleno siguen las hojas Rec y Prod de referencia.
    header_fill = PatternFill('solid', fgColor='FFFFC000')
    base_font = Font(name='Arial', size=10)
    group_font = Font(name='Arial', size=10, bold=True)
    header_font = Font(name='Arial', size=10)
    ws['A1'].font = group_font
    for cell in ws[3]:
        if cell.column <= final_col:
            cell.font = group_font
            cell.alignment = Alignment(horizontal='center')
    for cell in ws[4]:
        if cell.column <= final_col:
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
    for row in range(5, 5 + len(dates)):
        for col in range(1, final_col + 1):
            ws.cell(row, col).fill = header_fill
            ws.cell(row, col).font = base_font
        ws.cell(row, 1).number_format = 'dd-mm-yyyy'
        for col in range(2, final_col + 1):
            ws.cell(row, col).number_format = '0.00'
    ws.column_dimensions['A'].width = 46
    for col in range(2, final_col + 1):
        ws.column_dimensions[get_column_letter(col)].width = 11
    return ws


def hoja_resumen(doc):
    r = []
    for lab in ('OXIDOS', 'SULFUROS'):
        for q in doc['pads'].get(lab, {}).get('pilas', []):
            r.append({
                'Pad': lab, 'Pila': q['p'], 'Campana': q['campana'],
                'Apilado ini': q['apilado_ini'], 'Apilado fin': q['apilado_fin'],
                'Inicio riego': q['ini'], 'Dias ciclo': q['n'],
                'Dias con riego': q['dias_riego'], 'Dias con ley PLS': q['dias_ley'],
                'TMS': q['tms'], 'Ley CuT [%]': q['ley'],
                'Apilado tmf [t]': q['apilado'],
                'Riego acum [m3]': q['vol_riego'], 'RL [m3/t]': q['rl'],
                'Cu medido [t]': q['t_med'], 'Cu reconciliado [t]': q['t_rec'],
                'Delta recon [t]': round(q['t_rec'] - q['t_med'], 3),
                'Recuperacion [%]': q['pct'],
                'Recuperacion al %s [%%]' % _corte_corto(doc): q['pct_corte'],
                'En hoja de planta': ('si' if q['planta_ok'] else 'NO'),
            })
    return pd.DataFrame(r)


def hoja_comparacion(doc):
    r = []
    for lab in ('OXIDOS', 'SULFUROS'):
        for q in doc['pads'].get(lab, {}).get('pilas', []):
            ap_pl = q['planta_apilado']
            r.append({
                'Pad': lab, 'Pila': q['p'], 'Campana': q['campana'],
                'Campana planta': q['planta_campana'],
                'Ciclos nuestro': q['n'], 'Ciclos planta': q['planta_ciclos'],
                'Apilado tmf DB': q['apilado'], 'Apilado tmf planta': ap_pl,
                'Delta apilado [t]': (round(q['apilado'] - ap_pl, 3) if ap_pl else None),
                'Rec nuestra al %s [%%]' % _corte_corto(doc): q['pct_corte'],
                'Rec planta [%]': q['planta_pct'],
                'Delta [pts]': (round(q['pct_corte'] - q['planta_pct'], 3)
                                if (q['pct_corte'] is not None and q['planta_pct']) else None),
                'Rec nuestra al %s [%%]' % doc['end']: q['pct'],
            })
    return pd.DataFrame(r)


def graficos(w, doc, label):
    """Una hoja por pad con la curva en % y la curva en toneladas."""
    P = sorted(doc.get('pads', {}).get(label, {}).get('pilas', []),
               key=lambda q: ORDEN[label].index(q['num']))
    ws = w.book.create_sheet(CHART[label])
    for row in range(1, 75):
        ws.row_dimensions[row].height = 15
    if not P:
        ws['A1'] = 'Sin pilas con datos para este pad.'
        return
    nmax = max(q['n'] for q in P)
    n = len(P)
    src = w.book[HOJA[label]]        # la hoja de datos ya trae la curva en %

    # En el formato de planta Oxidos guarda ids en la fila 9 y curva desde 10;
    # Sulfuros deja fila 9 vacia, ids en 10 y curva desde 11.
    r0 = 10 if label == 'OXIDOS' else 11
    r1 = r0 + nmax - 1

    ws.cell(row=1, column=COL_T, value='dia')
    for j, q in enumerate(P):
        ws.cell(row=1, column=COL_T + 1 + j, value=q['p'])
        for i, v in enumerate(q['rec']):
            ws.cell(row=2 + i, column=COL_T + 1 + j, value=v)
    for i in range(nmax):
        ws.cell(row=2 + i, column=COL_T, value=i + 1)

    def linea(titulo, ytit, hoja, c_ini, f_ini, f_fin, c_cat):
        ch = LineChart()
        ch.title = titulo
        ch.y_axis.title = ytit
        ch.x_axis.title = 'dia de ciclo'
        ch.height, ch.width = 15.5, 33
        ch.style = 2
        for j in range(n):
            s = Series(Reference(hoja, min_col=c_ini + j,
                                 min_row=f_ini, max_row=f_fin),
                       title=P[j]['p'])
            s.marker = Marker(symbol='none')
            s.smooth = False
            ch.series.append(s)
        ch.set_categories(Reference(hoja, min_col=c_cat,
                                    min_row=f_ini, max_row=f_fin))
        return ch

    ws.add_chart(linea('%s - recuperacion acumulada' % label.title(),
                       '% del Apilado tmf', src, 2, r0, r1, 1), 'A1')
    ws.add_chart(linea('%s - Cu fino acumulado' % label.title(),
                       't Cu', ws, COL_T + 1, 2, 1 + nmax, COL_T), 'A38')
    ws.column_dimensions[get_column_letter(COL_T)].width = 6


def notas(doc):
    casos = ', '.join(str(c['id']) for c in doc.get('casos', []))
    return [
        ('Reporte de recuperaciones por el metodo reconciliado', ''),
        ('Corte de datos', doc['end']),
        ('Corte del reporte de planta comparado', doc['corte_planta']),
        ('Casos con ancla usados', casos or 'ninguno'),
        ('', ''),
        ('Origen de cada dato', ''),
        ('Apilado tmf', 'SUM(Finos_cut) de modulos_turnos por pad, parcela y campana. '
                        'Finos_cut = TMS * CuT_TM / 100. Calza exacto con el Apilado tmf '
                        'de la planta en 53 de 60 pilas.'),
        ('Campana de cada pila', 'la campana con apilado mas reciente en modulos_turnos.'),
        ('Inicio de ciclo', 'primer dia con riego > 0 despues de terminado el apilado de esa '
                            'campana. Reproduce exacto el Ciclos de planta en las pilas de un '
                            'solo bloque de riego.'),
        ('Extraccion diaria', 'ext [t Cu/dia] = (Q_dren * Cu_PLS - Q_riego * Cu_refino) * 0,024. '
                              'El 0,024 es solo conversion de unidades: Q en m3/h por 24 h/dia '
                              'por 1000 L/m3 dividido por 1e6 g/t. Dentro de las ventanas con '
                              'ancla van el Q y el Cu reconciliados por el motor; fuera de '
                              'ellas van las leyes medidas de la DB con el Fdrenaje base, '
                              'Q_dren = 0,95 * Q_riego. Cada dia pertenece a un solo caso.'),
        ('Caudal de drenaje', 'La DB no tiene caudal de drenaje por pila: solo quimica de drenaje '
                              'por parcela y riego por parcela. Fuera de las ventanas rige el '
                              'Fdrenaje base FDRENA_MAX = 0,95; dentro de ellas el motor lo ajusta '
                              'por pila y por dia contra el ancla. La unica medicion de drenaje '
                              'disponible es de pad (pila_pls_sx, solo 2025-07 a 2025-12) y da '
                              '0,94 en oxidos y 0,90 en sulfuros, o sea el 0,95 base queda por el '
                              'lado alto.'),
        ('', ''),
        ('Diferencias contra el reporte de planta', ''),
        ('1', 'La hoja de planta esta vencida al 31-07-2026: oxidos P17 ya se re-apilo en '
              'campana 18 y sulfuros P23 y P24 en campana 11. Esas pilas arrancaron ciclo '
              'nuevo y no son comparables con la hoja.'),
        ('2', 'La fila Ciclos de la planta es solo la etiqueta del eje de dias, no la ventana '
              'de integracion: la planta acumula la campana completa y reinicia el contador '
              'tras cada descanso. Por eso nuestro Ciclos sale mas largo en las pilas viejas '
              'aunque el acumulado en toneladas si sea comparable.'),
        ('3', 'La fila Aporte Parcelas de la hoja de planta es incoherente con su propia '
              'Recuperacion max. en 43 de 60 columnas (P12 de oxidos trae 0,00 con 75,9 % de '
              'recuperacion; P13 trae 2.552 t sobre un apilado de 1.014 t). No se uso.'),
        ('4', 'Este reporte no busca reproducir el numero de la planta: son dos metodos '
              'distintos sobre los mismos datos crudos y la hoja de planta se usa solo como '
              'referencia. La diferencia es sistematica y en una sola direccion, mediana '
              '+13,7 puntos y rango -6,1 a +41,8, sin pilas descolgadas. Eso indica un offset '
              'de escala, no errores puntuales. El parametro que fija esa escala es el Q PLS '
              'fijo en 0,95 x Q riego, unica constante libre del calculo.'),
        ('', ''),
        ('Supuesto', 'Fuera de las ventanas con ancla rige Q_dren = 0,95 * Q_riego. Mientras no '
                     'se mida el caudal de drenaje por pila, los puntos ganados dentro de una '
                     'ventana son comparables entre si y entre pilas; la recuperacion absoluta '
                     'arrastra ese supuesto.'),
        ('Advertencia', 'Quedan pilas sobre 100 % de recuperacion. La planta misma reporta '
                        'oxidos P09 en 107,2 % y P17..P19 sobre 103 %, o sea el fenomeno existe '
                        'en los dos metodos. Candidatos: (a) el Fdrenaje base 0,95 queda alto, '
                        'el pad medido da 0,90..0,94; (b) el Apilado tmf esta subestimado; '
                        '(c) hay aporte de soluciones de pilas vecinas al punto de muestreo. '
                        'No es un error de integracion de la curva.'),
    ]


def escribir_libro(doc, out_path):
    """Rec Ox, Rec Sulfuro, las dos hojas de gráficos y Prod diaria.

    Las hojas Resumen, Comparacion planta y Metodo se sacaron del libro. Sus
    constructores (`hoja_resumen`, `hoja_comparacion`, `notas`) se conservan
    intactos: no los llama nadie mas hoy, pero son el texto de metodologia y
    los agregados por pad, y reponerlos es agregar la linea de vuelta aca.
    """
    pads = ['OXIDOS', 'SULFUROS']
    with pd.ExcelWriter(out_path, engine='openpyxl', datetime_format='dd-mm-yyyy') as w:
        for lab in pads:
            ws = w.book.create_sheet(HOJA[lab])
            _escribir_hoja_pad(ws, doc, lab)
        for lab in pads:
            graficos(w, doc, lab)
        _escribir_prod(w, doc)

    return out_path

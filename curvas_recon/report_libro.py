# -*- coding: utf-8 -*-
"""Escritura del libro de recuperaciones con el formato del reporte oficial.

Las 15 hojas visibles, en el orden del oficial:

  Oxido, Sulfuro (graficos agrupados), Dump,
  Rec Ox, Rec Ox 2, Prod Cu Oxidos, (Cu) dren Ox, Flujo Riego Ox, RL Oxidos,
  Rec Sulfuro, Rec Sulfuro 2, Prod Cu Sulfuros, (Cu) dren Sulf.,
  Flujo Riego Sulf, RL Sulfuro.

Cadena de calculo (como en el oficial, con formulas vivas):
``Prod Cu *`` (t Cu/dia, valores) -> ``Rec * 2`` (recuperacion acumulada [%] por
fecha) -> ``Rec Ox`` / ``Rec Sulfuro`` (curva por dia de ciclo y encabezado con
LOOKUP / MAX / SUM) -> graficos y ``RL *``. Lo que el oficial toma de libros
externos (``[3]`` / ``[4]``: Apilado tmf, Cu de drenaje, riego, RL) va aqui como
valor. Las columnas de fechas son valores, no ``=A5+1``, para que cualquier
lector (pandas incluido) vea el calendario sin recalcular.
"""
import math
from copy import copy

import pandas as pd
from openpyxl.cell.cell import Cell
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.styles.colors import Color
from openpyxl.utils import get_column_letter

from . import report_layout as L
from .report_charts import (ANCLA_VIRTUAL, GRUPOS, TAMANO, TAMANO_RL, TITULOS_RL,
                            Y_MAX_RL, agregar_serie, escala, nuevo_grafico)
from .report_columns import physical_columns, recovery_columns, with_group_columns

ARIAL = Font(name='Arial', size=10)
ARIAL_B = Font(name='Arial', size=10, bold=True)
DERECHA = Alignment(horizontal='right')
CENTRO = Alignment(horizontal='center')
AMARILLO = PatternFill('solid', fgColor='FFFFFF00')
CELESTE = PatternFill('solid', fgColor='FFCCECFF')
NARANJA = PatternFill('solid', fgColor='FFFFC000')


# ── utilidades ───────────────────────────────────────────────────────────────

def _pon(cell, font=ARIAL, fill=None, fmt='General', align=None):
    """Aplica un estilo a una celda reutilizando el StyleArray ya registrado.

    Asignar font/fill/number_format celda a celda es el cuello de botella de
    openpyxl en hojas de decenas de miles de celdas; aqui cada combinacion se
    registra una sola vez por libro y luego se copia el indice.
    """
    book = cell.parent.parent
    cache = book.__dict__.setdefault('_estilos_reporte', {})
    key = (id(font), id(fill) if fill is not None else 0, fmt,
           id(align) if align is not None else 0)
    if key not in cache:
        plantilla = Cell(cell.parent)
        plantilla.font = font
        if fill is not None:
            plantilla.fill = fill
        plantilla.number_format = fmt
        if align is not None:
            plantilla.alignment = align
        cache[key] = copy(plantilla._style)
    cell._style = copy(cache[key])
    return cell


def _hoja(book, nombre):
    """La hoja `nombre`, creandola si no existe."""
    return book[nombre] if nombre in book.sheetnames else book.create_sheet(nombre)


def _formato_hoja(ws):
    """Color de pestana, anchos y panel inmovilizado del oficial."""
    color = L.COLOR_PESTANA.get(ws.title)
    if color:
        ws.sheet_properties.tabColor = (Color(theme=color[1]) if isinstance(color, tuple)
                                        else Color(rgb=color))
    for (lo, hi), width in L.ANCHOS.get(ws.title, {}).items():
        for idx in range(lo, hi + 1):
            ws.column_dimensions[get_column_letter(idx)].width = width
    if L.PANELES.get(ws.title):
        ws.freeze_panes = L.PANELES[ws.title]


def crear_hojas(book):
    """Crea (en orden) las 15 hojas del oficial y les da su formato base."""
    for nombre in L.ORDEN_HOJAS:
        _formato_hoja(_hoja(book, nombre))
    if 'Sheet' in book.sheetnames and not book['Sheet'].max_row > 1:
        del book['Sheet']


def _num(value):
    """float finito o None."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _ini(doc, label, q):
    pad = (doc.get('pads') or {}).get(label) or {}
    return pd.Timestamp(q.get('ini') or pad.get('desde') or doc.get('end')).normalize()


def _curva_pct(q):
    """Curva visible en % del Apilado tmf: lista con None en los huecos."""
    ap = _num(q.get('apilado'))
    if not ap:
        return []
    curva = q.get('rec_curve', q.get('rec')) or []
    return [round(float(v) * 100.0 / ap, 6) if _num(v) is not None else None for v in curva]


def _orden(doc, label):
    """Numeros de pila en el orden de las columnas fisicas (extras al final)."""
    return [int(q['num']) for q in physical_columns(doc, label, L.ORDEN[label])]


def _extra(doc, label):
    """Pilas fuera de las NPILAS del oficial (desplazan PH / Total Prod)."""
    return max(0, len(_orden(doc, label)) - L.NPILAS[label])


def _posicion_rec(doc, label):
    """{id de columna: columna en la hoja Rec} para fisicas y grupos virtuales."""
    cols = recovery_columns(doc, label, L.ORDEN[label])
    return {id(q): idx for idx, q in enumerate(cols, start=2)}


# ── Rec Ox / Rec Sulfuro ─────────────────────────────────────────────────────

def _escribir_hoja_pad(ws, doc, label):
    """Hoja Rec: encabezado de 8 filas, numero de pila y curva por dia de ciclo."""
    geo = L.rec_geom(label)
    id_row, first = geo['id_row'], geo['first_row']
    g2 = L.rec2_geom(label)
    gp = L.prod_geom(label)
    fechas = L.pad_dates(doc, label)
    pilas = recovery_columns(doc, label, L.ORDEN[label])
    nmax = max((q['n'] for q in pilas), default=0)
    last = max(first, first + nmax - 1)
    rec2, prod = L.sheet_ref(L.HOJA2[label]), L.sheet_ref(L.HOJA_PROD[label])

    for row, etiqueta in enumerate(L.ETIQUETAS_REC, start=1):
        ws.cell(row=row, column=1, value=etiqueta)
    if label == 'SULFUROS':
        ws.cell(row=id_row, column=1, value='Dias Lix')
        ws.cell(row=id_row, column=1).alignment = Alignment(horizontal='center')
        ws.cell(row=id_row, column=1).font = ARIAL_B
    for i in range(nmax):
        ws.cell(first + i, 1, i + 1)

    for col, q in enumerate(pilas, start=2):
        letter = get_column_letter(col)
        ws.cell(id_row, col, q['num'])
        if not q['n']:
            continue
        virtual = bool(q.get('virtual'))
        ap = _num(q.get('apilado'))
        rt = _num(q.get('planta_rec_termino'))
        curva = _curva_pct(q)
        fisica = (not virtual and fechas is not None
                  and int(q['num']) in _orden(doc, label))
        ws.cell(1, col, q.get('campana'))
        ws.cell(2, col, f'=+LOOKUP({letter}3,{letter}{first}:{letter}{last},$A${first}:$A${last})')
        ws.cell(3, col, f'=+MAX({letter}{first}:{letter}{last})')
        if fisica:
            ini = _ini(doc, label, q)
            r0 = L.date_row(ini, fechas[0], gp['first_row'])
            r1 = r0 + int(q['n']) - 1
            pc = get_column_letter(L.pile_col(label, q['num'], gp['col0'], _orden(doc, label)))
            c2 = get_column_letter(L.pile_col(label, q['num'], g2['col0'], _orden(doc, label)))
            ws.cell(4, col, f'=+SUM({prod}!{pc}{r0}:{pc}{r1})')
            ws.cell(5, col, f'=+{rec2}!{c2}{g2["apilado_row"]}')
        else:
            final = q['rec'][-1] if q.get('rec') else q.get('t_rec')
            ws.cell(4, col, round(final, 3) if _num(final) is not None else None)
            ws.cell(5, col, ap)
        if rt is not None:
            ws.cell(6, col, rt)
            ws.cell(7, col, f'=+{letter}5*{letter}6/100')
            ws.cell(8, col, f'=+{letter}7-{letter}4')
        if not ap:
            continue
        for i, value in enumerate(curva):
            if value is None:
                continue
            if fisica:
                row2 = L.date_row(ini + pd.Timedelta(days=i), fechas[0], g2['first_row'])
                ws.cell(first + i, col, f'={rec2}!{c2}{row2}')
            else:
                ws.cell(first + i, col, value)

    # estilo del oficial
    max_row = last
    fmt = L.FMT_REC[label]
    ox = label == 'OXIDOS'
    for row in range(1, max_row + 1):
        _pon(ws.cell(row, 1), ARIAL_B if (row == id_row and not ox) else ARIAL,
             align=CENTRO if (row == id_row and not ox) else None)
    for col, q in enumerate(pilas, start=2):
        ws.column_dimensions[get_column_letter(col)].width = 24 if q.get('virtual') else 8.45
        for row in range(1, max_row + 1):
            if row == id_row:
                _pon(ws.cell(row, col), ARIAL_B, AMARILLO if ox else None, align=DERECHA)
            elif row <= 8:
                _pon(ws.cell(row, col),
                     ARIAL_B if (ox and row in (1, 6)) else ARIAL,
                     (AMARILLO if ox else CELESTE) if row == 6 else None,
                     fmt[row], DERECHA if (row == 6 and not ox) else None)
            elif row >= first:
                _pon(ws.cell(row, col), ARIAL, None, L.FMT_REC_DATOS, None if ox else DERECHA)
            else:
                _pon(ws.cell(row, col))


# ── Rec Ox 2 / Rec Sulfuro 2 ─────────────────────────────────────────────────

def _escribir_rec2(ws, doc, label):
    """Recuperacion acumulada [%] por pila y fecha: Prod * 100 / Apilado + dia previo."""
    g = L.rec2_geom(label)
    gp = L.prod_geom(label, _extra(doc, label))
    fechas = L.pad_dates(doc, label)
    pilas = physical_columns(doc, label, L.ORDEN[label])
    lab_row, lab_col = g['label_cell']
    ws.cell(lab_row, lab_col, 'Apilado tmf').number_format = (
        '#,##0' if label == 'OXIDOS' else 'General')
    ws.cell(g['pile_row'], g['date_col'], 'Parcela')
    prod = L.sheet_ref(L.HOJA_PROD[label])
    for q in pilas:
        col = L.pile_col(label, q['num'], g['col0'], _orden(doc, label))
        letter = get_column_letter(col)
        ws.cell(g['pile_row'], col, q['num'])
        ap = _num(q.get('apilado'))
        if not q.get('n') or not ap or fechas is None:
            continue
        ws.cell(g['apilado_row'], col, ap)
        pc = get_column_letter(L.pile_col(label, q['num'], gp['col0'], _orden(doc, label)))
        ini = _ini(doc, label, q)
        row0 = L.date_row(ini, fechas[0], g['first_row'])
        prow0 = L.date_row(ini, fechas[0], gp['first_row'])
        for i in range(int(q['n'])):
            formula = f'=+{prod}!{pc}{prow0 + i}*100/${letter}${g["apilado_row"]}'
            if i:
                formula += f'+{letter}{row0 + i - 1}'
            ws.cell(row0 + i, col, formula)
    if fechas is not None:
        n_days = (fechas[1] - fechas[0]).days + 1
        last_col = g['col0'] + len(pilas) - 1
        for i in range(n_days):
            day = fechas[0] + pd.Timedelta(days=i)
            _pon(ws.cell(g['first_row'] + i, g['date_col'], day.to_pydatetime()),
                 ARIAL, None, L.FMT_FECHA)
            for col in range(g['col0'], last_col + 1):
                _pon(ws.cell(g['first_row'] + i, col), ARIAL, None, L.FMT_REC2_DATOS)
    for col in range(g['col0'], g['col0'] + len(pilas)):
        _pon(ws.cell(g['apilado_row'], col), ARIAL, None, '#,##0')
        _pon(ws.cell(g['pile_row'], col), ARIAL, None, 'General', CENTRO)


# ── Prod Cu * ────────────────────────────────────────────────────────────────

def _caso_etiquetas(doc):
    labels = []
    for case in doc.get('casos', []):
        case_id = case.get('id')
        run_id = case.get('run', case.get('run_id'))
        start = case.get('desde') or case.get('fecha_inicio')
        end = case.get('hasta') or case.get('fecha_fin')
        period = f'{start}–{end}' if start and end else 'periodo no disponible'
        labels.append(f'Caso {case_id if case_id is not None else "no disponible"} / '
                      f'run {run_id if run_id is not None else "no disponible"} ({period})')
    return labels


def _escribir_prod(w, doc):
    """Prod Cu *: t Cu neto diario por pila, `Total Prod` diario y `Total Suma` mensual.

    `Total Prod` (formula) es la suma diaria de las pilas de esa fecha.
    `Total Suma` es la suma de `Total Prod` desde el primer dia del mes del
    corte hasta la fecha de corte: el rotulo va en la fila del dia 1 del mes y
    la formula en la fila siguiente, como en el oficial (`AL3384` / `AL3385`).
    """
    titles = {'OXIDOS': 'Óxidos', 'SULFUROS': 'Sulfuros'}
    for label in L.PADS:
        ws = _hoja(w.book, L.HOJA_PROD[label])
        _formato_hoja(ws)
        g = L.prod_geom(label, _extra(doc, label))
        pilas = physical_columns(doc, label, L.ORDEN[label])
        ws['A1'] = 'Cu neto diario [t Cu/dia]'
        ws['A2'] = ' | '.join(_caso_etiquetas(doc)) or f'Corte {doc.get("end")}'
        ws['A3'] = titles[label]
        ws['A4'] = 'Parcela'
        _pon(ws['A1'], ARIAL_B)
        _pon(ws['A3'], ARIAL_B, None, 'General', CENTRO)
        _pon(ws['A4'], ARIAL)
        for q in pilas:
            _pon(ws.cell(g['pile_row'], L.pile_col(label, q['num'], g['col0'], _orden(doc, label)),
                         q['num']), ARIAL, None, 'General', CENTRO)
        if g['ph_col']:
            _pon(ws.cell(g['pile_row'], g['ph_col'], 'PH'), ARIAL, None, 'General', CENTRO)
        ws.cell(g['pile_row'], g['total_col'], 'Total Prod')

        fechas = L.pad_dates(doc, label)
        if fechas is None:
            continue
        n_days = (fechas[1] - fechas[0]).days + 1
        first = g['first_row']
        for i in range(n_days):
            ws.cell(first + i, g['date_col'], (fechas[0] + pd.Timedelta(days=i)).to_pydatetime())
        for q in pilas:
            if not q.get('n'):
                continue
            col = L.pile_col(label, q['num'], g['col0'], _orden(doc, label))
            start = _ini(doc, label, q)
            previous = 0.0
            for i, cumulative in enumerate(q.get('rec') or []):
                value = _num(cumulative)
                if value is None:
                    continue
                row = L.date_row(start + pd.Timedelta(days=i), fechas[0], first)
                ws.cell(row, col, round(value - previous, 3))
                previous = value
        # Total Prod diario y su acumulado del mes hasta el corte
        last_pile_col = g['ph_col'] or (g['col0'] + len(pilas) - 1)
        c_first, c_last = get_column_letter(g['col0']), get_column_letter(last_pile_col)
        t_letter = get_column_letter(g['total_col'])
        for i in range(n_days):
            row = first + i
            ws.cell(row, g['total_col'], f'=+SUM({c_first}{row}:{c_last}{row})')
        corte = pd.Timestamp(doc.get('end') or fechas[1]).normalize()
        corte = min(max(corte, fechas[0]), fechas[1])
        mes0 = max(corte.replace(day=1), fechas[0])
        r_mes0 = L.date_row(mes0, fechas[0], first)
        r_corte = L.date_row(corte, fechas[0], first)
        ws.cell(r_mes0, g['suma_col'], 'Total Suma')
        ws.cell(r_mes0 + 1, g['suma_col'], f'=+SUM({t_letter}{r_mes0}:{t_letter}{r_corte})')

        fmt = L.FMT_PROD[label]
        for row in range(first, first + n_days):
            _pon(ws.cell(row, 1), ARIAL, NARANJA, L.FMT_FECHA)
            for col in range(g['col0'], g['total_col'] + 1):
                _pon(ws.cell(row, col), ARIAL, NARANJA if col <= last_pile_col else None, fmt)
        _pon(ws.cell(r_mes0 + 1, g['suma_col']), ARIAL_B, None, fmt)
        _pon(ws.cell(r_mes0, g['suma_col']), ARIAL_B)


# ── (Cu) dren * y Flujo Riego * ──────────────────────────────────────────────

def _escribir_dren(w, doc):
    """(Cu) dren *: ley de Cu del drenaje [g/L] por pila y dia (cabecera fila 4)."""
    for label in L.PADS:
        ws = _hoja(w.book, L.HOJA_DREN[label])
        _formato_hoja(ws)
        g = L.dren_geom(label, _extra(doc, label))
        pilas = physical_columns(doc, label, L.ORDEN[label])
        _pon(ws.cell(g['head_row'], 1, 'Cu++'), ARIAL, None, L.FMT_FECHA)
        fmt_cab = L.FMT_DREN['SULFUROS'] if label == 'SULFUROS' else 'General'
        for q in pilas:
            _pon(ws.cell(g['head_row'], L.pile_col(label, q['num'], g['col0'], _orden(doc, label)),
                         f'P{int(q["num"])}Cu++'), ARIAL, None, fmt_cab)
        if g['ph_col']:
            ws.cell(g['head_row'], g['ph_col'], 'PHCu++')
        fechas = L.pad_dates(doc, label)
        if fechas is None:
            continue
        n_days = (fechas[1] - fechas[0]).days + 1
        for i in range(n_days):
            _pon(ws.cell(g['first_row'] + i, 1, (fechas[0] + pd.Timedelta(days=i)).to_pydatetime()),
                 ARIAL, None, L.FMT_FECHA)
        for q in pilas:
            col = L.pile_col(label, q['num'], g['col0'], _orden(doc, label))
            serie = q.get('dren_cu_curve') or []
            for i, value in enumerate(serie[:n_days]):
                if _num(value) is not None:
                    _pon(ws.cell(g['first_row'] + i, col, value), ARIAL, None, L.FMT_DREN[label])


def _escribir_flujo(w, doc):
    """Flujo Riego *: m3/dia por pila y dia; filas 1-4 con RL y suma del ciclo."""
    for label in L.PADS:
        ws = _hoja(w.book, L.HOJA_FLUJO[label])
        _formato_hoja(ws)
        g = L.flujo_geom(label)
        pilas = physical_columns(doc, label, L.ORDEN[label])
        for row, etiqueta in enumerate(['RL/días de riego', 'RL', 'TMS apiladas', 'Sum riego',
                                        'Parcela'], start=1):
            ws.cell(row, 1, etiqueta)
        fechas = L.pad_dates(doc, label)
        for q in pilas:
            col = L.pile_col(label, q['num'], g['col0'], _orden(doc, label))
            _pon(ws.cell(g['pile_row'], col, q['num']), ARIAL, None, 'General', CENTRO)
        if fechas is None:
            continue
        n_days = (fechas[1] - fechas[0]).days + 1
        first = g['first_row']
        for i in range(n_days):
            _pon(ws.cell(first + i, 1, (fechas[0] + pd.Timedelta(days=i)).to_pydatetime()),
                 ARIAL, None, L.FMT_FECHA)
        for q in pilas:
            col = L.pile_col(label, q['num'], g['col0'], _orden(doc, label))
            letter = get_column_letter(col)
            serie = q.get('riego_curve') or []
            for i, value in enumerate(serie[:n_days]):
                if _num(value) is not None:
                    _pon(ws.cell(first + i, col, value), ARIAL, None, '0')
            tms = _num(q.get('tms'))
            if not q.get('n') or not tms:
                continue
            r0 = L.date_row(_ini(doc, label, q), fechas[0], first)
            r1 = L.date_row(fechas[0] + pd.Timedelta(days=n_days - 1), fechas[0], first)
            ws.cell(3, col, tms)
            ws.cell(4, col, f'=+SUM({letter}{r0}:{letter}{r1})')
            ws.cell(2, col, f'=+{letter}4/{letter}3')
            ws.cell(1, col, f'=({letter}2/(COUNTIF({letter}{r0}:{letter}{r1},">0")))*1000')
            for row, fmt in ((1, '0.000'), (2, '0.000'),
                             (3, '#,##0' if label == 'OXIDOS' else '0'), (4, '0')):
                _pon(ws.cell(row, col), ARIAL, None, fmt)


# ── RL * ─────────────────────────────────────────────────────────────────────

def _rl_values(doc, label, q):
    """RL acumulada por dia de ciclo, recortada al corte del reporte."""
    values = q.get('rl_accum_curve')
    if values is None:  # Compatibilidad con documentos antiguos.
        total, unknown, values = 0.0, False, []
        for value in q.get('rl_curve') or []:
            if value is None:
                unknown = True
                values.append(None)
            elif unknown:
                values.append(None)
            else:
                total += float(value)
                values.append(total)
    pad = (doc.get('pads') or {}).get(label) or {}
    cutoff = pd.Timestamp(doc.get('end') or pad.get('desde') or pd.Timestamp.today())
    known_start = q.get('ini') or pad.get('desde')
    start = pd.Timestamp(known_start or cutoff)
    n_visible = (max(0, min(len(values), (cutoff.normalize() - start.normalize()).days + 1))
                 if known_start else len(values))
    return values[:n_visible]


def _escribir_rl(w, doc):
    """RL acumulada por dia de ciclo (pilas ascendentes) y 4 graficos Recuperacion vs RL.

    Disposicion (las columnas fisicas no dependen de los grupos virtuales):
    A = dia de ciclo, B.. = RL de cada pila (como el oficial); a su derecha los
    graficos; mas a la derecha el bloque de recuperacion [%] por dia de ciclo
    (eje Y de los graficos, formulas que leen la hoja Rec); y, despues, un
    bloque equivalente para las pilas virtuales, si las hay.
    """
    for label in L.PADS:
        ws = _hoja(w.book, L.HOJA_RL[label])
        _formato_hoja(ws)
        fisicas = physical_columns(doc, label, L.ORDEN_RL[label])
        virtuales = list((doc.get('group_columns') or {}).get(label, []))
        todas = fisicas + virtuales
        nf = len(fisicas)
        pos_rec = _posicion_rec(doc, label)
        rec_name = L.sheet_ref(L.HOJA[label])
        first_rec = L.rec_geom(label)['first_row']
        series = {id(q): _rl_values(doc, label, q) for q in todas}
        n_days = max((len(v) for v in series.values()), default=0)

        sep = 8 if label == 'SULFUROS' else 7
        ancla_x = nf + 3
        rec0 = ancla_x + sep + 10
        vcol0 = rec0 + nf + 3
        vrec0 = vcol0 + len(virtuales) + 2
        col_rl, col_rec = {}, {}
        for i, q in enumerate(fisicas):
            col_rl[id(q)], col_rec[id(q)] = 2 + i, rec0 + 1 + i
        for j, q in enumerate(virtuales):
            col_rl[id(q)], col_rec[id(q)] = vcol0 + 1 + j, vrec0 + 1 + j

        _pon(ws.cell(1, 1, 'Parcela'))
        _pon(ws.cell(1, rec0, 'Recuperación [%]'), ARIAL_B)
        if virtuales:
            _pon(ws.cell(1, vcol0, 'RL pilas virtuales'), ARIAL_B)
            _pon(ws.cell(1, vrec0, 'Recuperación [%] pilas virtuales'), ARIAL_B)
        for day_idx in range(n_days):
            for col in (1, rec0) + ((vcol0, vrec0) if virtuales else ()):
                _pon(ws.cell(day_idx + 2, col, day_idx + 1))
        for q in todas:
            _pon(ws.cell(1, col_rl[id(q)], q['num']), ARIAL, None, 'General', CENTRO)
            _pon(ws.cell(1, col_rec[id(q)], q['num']), ARIAL, None, 'General', CENTRO)
            values = series[id(q)]
            for day_idx, value in enumerate(values):
                if _num(value) is not None:
                    _pon(ws.cell(day_idx + 2, col_rl[id(q)], value), ARIAL, None, L.FMT_RL)
            src = pos_rec.get(id(q))
            curva = _curva_pct(q)
            if not src or not q.get('n'):
                continue
            letter = get_column_letter(src)
            con_formula = _usa_formulas(doc, label, q)
            for i, value in enumerate(curva[:n_days]):
                if value is None:
                    continue
                _pon(ws.cell(i + 2, col_rec[id(q)],
                             f'=+{rec_name}!{letter}{first_rec + i}' if con_formula else value),
                     ARIAL, None, '0.00')
        if n_days:
            _graficos_rl(ws, label, fisicas, virtuales, col_rl, col_rec, n_days, ancla_x, sep)


def _usa_formulas(doc, label, q):
    return bool(not q.get('virtual') and L.pad_dates(doc, label) is not None
                and _num(q.get('apilado')) and int(q['num']) in _orden(doc, label))


def _maximo(valores):
    finitos = [v for v in valores if v is not None]
    return max(finitos) if finitos else None


def _graficos_rl(ws, label, fisicas, virtuales, col_rl, col_rec, n_days, ancla_x, sep):
    por_num = {q['num']: q for q in fisicas}
    ancho, alto = TAMANO_RL
    filas = (2, 22) if label == 'OXIDOS' else (2, 24)
    posiciones = [(ancla_x, filas[0]), (ancla_x + sep, filas[0]),
                  (ancla_x, filas[1]), (ancla_x + sep, filas[1])]
    last = n_days + 1

    def construir(titulo, miembros, y_max_oficial):
        pct_max = _maximo([v for q in miembros for v in _curva_pct(q)])
        grafico = nuevo_grafico(
            titulo, ancho, alto, eje_x_titulo='RL', eje_y_titulo='Recuperación',
            y_max=escala(pct_max, y_max_oficial, 10), x_min=None, y_min=None,
            x_formato='0.00' if label == 'SULFUROS' else 'General', rejilla_x=False)
        for idx, q in enumerate(miembros):
            col_x = col_rl[id(q)]
            agregar_serie(grafico, ws, col_x, ws, col_rec[id(q)], 2, last, None,
                          f"{L.sheet_ref(ws.title)}!${get_column_letter(col_x)}$1", idx)
        return grafico

    for (lo, hi, *_), titulo, y_max, (col, row) in zip(
            GRUPOS[label], TITULOS_RL[label], Y_MAX_RL[label], posiciones):
        miembros = [por_num[n] for n in range(lo, hi + 1) if n in por_num]
        if miembros:
            ws.add_chart(construir(titulo, miembros, y_max), f'{get_column_letter(col)}{row}')
    if virtuales:
        ws.add_chart(construir('Recuperación vs RL (pilas virtuales)', virtuales, 80),
                     f'{get_column_letter(ancla_x)}{filas[1] + 20}')


# ── Oxido / Sulfuro: graficos de extraccion ─────────────────────────────────

def _escribir_graficos(w, doc, label):
    """Hoja `Oxido` / `Sulfuro`: 4 graficos de % de extraccion por grupo de pilas."""
    ws = _hoja(w.book, L.HOJA_GRAFICOS[label])
    _formato_hoja(ws)
    pilas = recovery_columns(doc, label, L.ORDEN[label])
    nmax = max((q['n'] for q in pilas), default=0)
    if not nmax:
        return
    src = _hoja(w.book, L.HOJA[label])
    geo = L.rec_geom(label)
    id_row, first = geo['id_row'], geo['first_row']
    last = first + nmax - 1
    col_de = {q['num']: idx for idx, q in enumerate(pilas, start=2) if not q.get('virtual')}
    ancho, alto = TAMANO[label]
    nombre_src = L.sheet_ref(L.HOJA[label])

    def construir(titulo, miembros, x_max, y_max):
        dias = max((q['n'] for _, q in miembros), default=0)
        pct_max = _maximo([v for _, q in miembros for v in _curva_pct(q)])
        grafico = nuevo_grafico(
            titulo, ancho, alto, eje_y_titulo='% Extracción Cu',
            x_max=escala(dias, x_max, 30), y_max=escala(pct_max, y_max, 10),
            x_unidad=30)
        for idx, (col, q) in enumerate(miembros):
            agregar_serie(grafico, src, 1, src, col, first, last, None,
                          f'{nombre_src}!${get_column_letter(col)}${id_row}', idx)
        return grafico

    for lo, hi, titulo, ancla, x_max, y_max in GRUPOS[label]:
        miembros = [(col_de[n], pilas[col_de[n] - 2]) for n in range(lo, hi + 1) if n in col_de]
        if miembros:
            ws.add_chart(construir(titulo, miembros, x_max, y_max), ancla)
    virtuales = [(idx, q) for idx, q in enumerate(pilas, start=2) if q.get('virtual')]
    if virtuales:
        ws.add_chart(construir('% Extracción pilas virtuales', virtuales, 360, 100),
                     ANCLA_VIRTUAL[label])


# ── Dump ─────────────────────────────────────────────────────────────────────

def _escribir_dump(w, doc):
    """Dump: forma oficial de 6 columnas. Ver `report_dump` para la regla."""
    rows = doc.get('dump') or []
    ws = _hoja(w.book, L.HOJA_DUMP)
    _formato_hoja(ws)
    headers = ['Fecha', 'Aporte', 'Flujo riego dump [m3/dia]',
               'Flujo salida dump [m3/dia]', 'Concentracion riego ',
               'Concentracion drenaje']
    ws.append(headers)
    for row in rows:
        ws.append([pd.Timestamp(row['fecha']).to_pydatetime() if row.get('fecha') is not None else None,
                   row.get('aporte'), row.get('flujo_riego'), row.get('flujo_salida'),
                   row.get('cu_feed'), row.get('cu_drenaje')])
    ws.freeze_panes = 'A2'
    for cell in ws[1]:
        cell.font = Font(name='Arial', size=11, bold=True)
        cell.fill = PatternFill('solid', fgColor=Color(theme=5))
        cell.alignment = Alignment(horizontal='center')
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name='Arial', size=9)
        row[0].number_format = L.FMT_FECHA
        for col in (1, 2, 3):
            row[col].number_format = '0'
        for col in (4, 5):
            row[col].number_format = '0.00'
    avisos = ' '.join(doc.get('dump_avisos') or [])
    w.book.properties.description = (
        'Hoja Dump reconciliada por Caso: riego (F77) y drenaje (F51) del run '
        'oficial. Factor de drenaje global F = Σ drenaje reconciliado / Σ riego '
        'reconciliado; riego diario = riego medido × (Σ riego reconciliado / Σ '
        'riego medido); drenaje diario = F × riego reconciliado diario; Aporte '
        '[t Cu/día] = (Qd·Cd − Qr·Cr)/1000 con Q en m3/día y C en g/L. '
        'Concentraciones medidas. Días fuera de un Caso oficial en blanco. ' + avisos).strip()


# ── libro completo ───────────────────────────────────────────────────────────

def escribir_libro(doc, out_path, groups=None):
    """Escribe el libro de 15 hojas con el formato del reporte oficial."""
    doc = with_group_columns(doc, groups)
    with pd.ExcelWriter(out_path, engine='openpyxl') as w:
        crear_hojas(w.book)
        for label in L.PADS:
            _escribir_hoja_pad(w.book[L.HOJA[label]], doc, label)
            _escribir_rec2(w.book[L.HOJA2[label]], doc, label)
        _escribir_prod(w, doc)
        _escribir_dren(w, doc)
        _escribir_flujo(w, doc)
        _escribir_rl(w, doc)
        for label in L.PADS:
            _escribir_graficos(w, doc, label)
        _escribir_dump(w, doc)
    return out_path

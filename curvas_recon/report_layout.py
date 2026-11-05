# -*- coding: utf-8 -*-
"""Geometria y formato compartidos del libro de recuperaciones.

Reproduce, hoja por hoja, la disposicion del reporte oficial
(`Reporte_Recuperaciones_12_de_Octubre_2026.xlsx`): nombres, orden, filas de
encabezado, columnas por pila, formatos numericos y anchos. Solo se replican
las 15 hojas visibles; las ocultas (`Budget FY16 y Q1`, `Rec Ox_gr`,
`Rec Sulfuro_gr`) no se escriben y las series de grafico que dependian de ellas
se omiten.

Este modulo no escribe nada: solo constantes y funciones puras de posicion.
"""
import pandas as pd
from openpyxl.utils import get_column_letter

PADS = ('OXIDOS', 'SULFUROS')
NPILAS = {'OXIDOS': 32, 'SULFUROS': 28}
# Orden de las columnas por pila: sulfuros va P21..P28, P1..P20; oxidos P1..P32.
ORDEN = {'OXIDOS': list(range(1, 33)),
         'SULFUROS': list(range(21, 29)) + list(range(1, 21))}
# RL (hoja y bloque de recuperacion) lista las pilas en orden ascendente.
ORDEN_RL = {'OXIDOS': list(range(1, 33)), 'SULFUROS': list(range(1, 29))}

HOJA = {'OXIDOS': 'Rec Ox', 'SULFUROS': 'Rec Sulfuro'}
HOJA2 = {'OXIDOS': 'Rec Ox 2', 'SULFUROS': 'Rec Sulfuro 2'}
HOJA_PROD = {'OXIDOS': 'Prod Cu Oxidos', 'SULFUROS': 'Prod Cu Sulfuros'}
HOJA_DREN = {'OXIDOS': '(Cu) dren Ox', 'SULFUROS': '(Cu) dren Sulf.'}
HOJA_FLUJO = {'OXIDOS': 'Flujo Riego Ox', 'SULFUROS': 'Flujo Riego Sulf'}
HOJA_RL = {'OXIDOS': 'RL Oxidos', 'SULFUROS': 'RL Sulfuro'}
HOJA_GRAFICOS = {'OXIDOS': 'Oxido', 'SULFUROS': 'Sulfuro'}
HOJA_DUMP = 'Dump'

# Orden exacto de las 15 hojas visibles del oficial.
ORDEN_HOJAS = [
    'Oxido', 'Sulfuro', 'Dump', 'Rec Ox', 'Rec Ox 2', 'Prod Cu Oxidos',
    '(Cu) dren Ox', 'Flujo Riego Ox', 'RL Oxidos', 'Rec Sulfuro',
    'Rec Sulfuro 2', 'Prod Cu Sulfuros', '(Cu) dren Sulf.',
    'Flujo Riego Sulf', 'RL Sulfuro']

ETIQUETAS_REC = ['Campaña', 'Ciclos', 'Recuperación máx.', 'Aporte Parcelas',
                 'Apilado tmf', 'Rec por especie', 'Recuperable', 'WIP']

# Colores de pestana del oficial: 'rgb' ARGB o ('theme', n).
COLOR_PESTANA = {
    'Oxido': 'FF00B050', 'Sulfuro': ('theme', 3), 'Rec Ox': 'FF00B050',
    'Rec Ox 2': 'FF00B050', 'Prod Cu Oxidos': 'FF00B050',
    '(Cu) dren Ox': 'FF00B050', 'Flujo Riego Ox': 'FF00B050',
    'RL Oxidos': 'FF00B050', 'Rec Sulfuro': ('theme', 3),
    'Rec Sulfuro 2': ('theme', 3), 'Prod Cu Sulfuros': ('theme', 3),
    '(Cu) dren Sulf.': ('theme', 3), 'Flujo Riego Sulf': ('theme', 3),
    'RL Sulfuro': ('theme', 1), 'Dump': None}

# Paneles inmovilizados del oficial (algunos son raros a proposito: se copian).
PANELES = {
    'Dump': 'A2', 'Rec Ox': 'B10', 'Rec Ox 2': 'A4', 'Prod Cu Oxidos': 'B3',
    '(Cu) dren Ox': 'B5', 'Flujo Riego Ox': 'B6', 'Rec Sulfuro': 'B11',
    'Rec Sulfuro 2': 'D5', 'Prod Cu Sulfuros': 'B5', '(Cu) dren Sulf.': 'B5',
    'Flujo Riego Sulf': 'B6'}

# Anchos de columna del oficial (chars). Clave: (primera, ultima) 1-based.
ANCHOS = {
    'Oxido': {(1, 1): 11.45, (2, 2): 25.45, (3, 20): 11.45},
    'Sulfuro': {(1, 1): 26.45, (2, 2): 11.45, (3, 3): 11.0, (4, 20): 10.45},
    'Dump': {(1, 1): 10.73, (2, 2): 10.63, (3, 3): 21.91, (4, 4): 15.82,
             (5, 5): 18.54, (6, 6): 20.18},
    'Rec Ox': {(1, 1): 17.45, (2, 2): 8.45, (3, 3): 9.45},
    'Rec Ox 2': {(1, 1): 9.45, (2, 3): 12.45, (4, 4): 13.45, (5, 8): 11.45},
    'Prod Cu Oxidos': {(1, 1): 15.0, (2, 34): 11.45},
    '(Cu) dren Ox': {(1, 1): 15.45},
    'Flujo Riego Ox': {(1, 1): 14.45, (2, 14): 11.45},
    'RL Oxidos': {},
    'Rec Sulfuro': {(1, 1): 17.45, (2, 13): 8.45, (14, 29): 8.0},
    'Rec Sulfuro 2': {(1, 2): 4.45, (3, 3): 12.0, (4, 6): 11.45},
    'Prod Cu Sulfuros': {(1, 1): 12.45, (2, 30): 9.45},
    '(Cu) dren Sulf.': {(1, 1): 12.54, (2, 29): 9.45},
    'Flujo Riego Sulf': {(1, 1): 11.45, (2, 9): 11.45, (10, 29): 10.45},
    'RL Sulfuro': {}}

# Formatos numericos del oficial.
FMT_FECHA = 'mm-dd-yy'
FMT_REC = {   # (fila de encabezado) -> formato, por pad; datos aparte
    'OXIDOS': {1: '0', 2: 'General', 3: '0.0', 4: '0.0', 5: '0.0', 6: '0.0',
               7: '0.0', 8: '0.0'},
    'SULFUROS': {1: 'General', 2: 'General', 3: '0.00', 4: '0', 5: '0.00',
                 6: '0.00', 7: '0.0', 8: '0.0'}}
FMT_REC_DATOS = '0.00'
FMT_REC2_DATOS = '#,##0.00'
FMT_PROD = {'OXIDOS': '0.00', 'SULFUROS': '#,##0.00'}
FMT_DREN = {'OXIDOS': '#,##0.0', 'SULFUROS': '#,##0.00'}
FMT_RL = '0.00'


# ── geometria por pad ────────────────────────────────────────────────────────

def col_letter(idx):
    return get_column_letter(idx)


def rec_geom(label):
    """Hoja Rec: fila de numeros de pila y primera fila de la curva."""
    return dict(id_row=9, first_row=10) if label == 'OXIDOS' else dict(id_row=10, first_row=11)


def rec2_geom(label):
    """Hoja Rec * 2: columna de fechas, primera columna de pila, filas."""
    if label == 'OXIDOS':
        return dict(date_col=2, col0=3, pile_row=5, first_row=6, apilado_row=3,
                    label_cell=(3, 2))
    return dict(date_col=3, col0=4, pile_row=4, first_row=5, apilado_row=1,
                label_cell=(1, 3))


def prod_geom(label, extra=0):
    """Hoja Prod: pilas desde la columna B; PH (solo oxidos) y Total Prod.

    `extra` desplaza PH / Total Prod si el pad trae pilas fuera de las NPILAS.
    """
    n = NPILAS[label] + extra
    total_col = 2 + n + (2 if label == 'OXIDOS' else 1)
    return dict(date_col=1, col0=2, pile_row=4, first_row=5,
                ph_col=(2 + n) if label == 'OXIDOS' else None,
                total_col=total_col, suma_col=total_col + 2)


def dren_geom(label, extra=0):
    n = NPILAS[label] + extra
    return dict(date_col=1, col0=2, head_row=4, first_row=5,
                ph_col=(2 + n) if label == 'OXIDOS' else None)


def flujo_geom(label):
    return dict(date_col=1, col0=2, pile_row=5, first_row=6)


def pile_col(label, num, col0, orden=None):
    """Columna (1-based) de la pila `num` segun el orden del pad."""
    orden = orden or ORDEN[label]
    return col0 + list(orden).index(int(num))


def pad_dates(doc, label):
    """Calendario comun de las hojas diarias de un pad: (inicio, fin) o None.

    Arranca en el inicio de ciclo mas antiguo (``desde``) y llega al ultimo dia
    de cualquier pila. Las pilas ausentes no aportan fechas.
    """
    pad = (doc.get('pads') or {}).get(label) or {}
    piles = [q for q in pad.get('pilas', []) if q.get('n')]
    starts = [pd.Timestamp(q.get('ini') or pad.get('desde')) for q in piles]
    if not starts:
        return None
    start = min(starts)
    if pad.get('desde'):
        start = min(start, pd.Timestamp(pad['desde']))
    end = max(pd.Timestamp(q.get('ini') or pad.get('desde')) + pd.Timedelta(days=int(q['n']) - 1)
              for q in piles)
    return start.normalize(), end.normalize()


def date_row(day, start, first_row):
    """Fila de la fecha `day` en una hoja diaria que arranca en `start`."""
    return first_row + (pd.Timestamp(day).normalize() - pd.Timestamp(start).normalize()).days


def sheet_ref(name):
    """Nombre de hoja entre comillas para usar en una formula."""
    return "'%s'" % name.replace("'", "''")

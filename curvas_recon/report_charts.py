# -*- coding: utf-8 -*-
"""Graficos agrupados del libro de recuperaciones (dispersion, como el oficial).

`Oxido` / `Sulfuro`: "% Extraccion" por grupo de pilas contra el dia de ciclo.
`RL Oxidos` / `RL Sulfuro`: "Recuperacion vs RL" por grupo, X = RL acumulada.

Colores, grosor (1,5 pt), curva suavizada sin marcadores, leyenda inferior,
ejes con rejilla y escalas replican los graficos del oficial. Solo se
referencian celdas de hojas visibles del propio libro: las series del oficial
que leian hojas ocultas (`Budget FY16 y Q1`, `Rec Ox_gr`) o libros externos
(`[3]`, `[4]`) no se reproducen; cada grupo trae sus pilas reales.
"""
import math

from openpyxl.chart import Reference, ScatterChart, Series
from openpyxl.chart.series import SeriesLabel
from openpyxl.chart.data_source import StrRef
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.colors import ColorChoice, SchemeColor
from openpyxl.drawing.line import LineProperties
from openpyxl.drawing.text import CharacterProperties

# Grupos de pilas por grafico: (primera, ultima, titulo, ancla, x_max, y_max)
GRUPOS_OXIDO = [
    (1, 8, '% Extracción Parcelas 1-8 Óxidos', 'B3', 360, 100),
    (9, 16, '% Extracción Parcelas 9-16 Óxidos', 'N3', 360, 110),
    (17, 24, '% Extracción Parcelas 17-24 Óxidos', 'B45', 400, 110),
    (25, 32, '% Extracción Parcelas 25-32 Óxidos', 'N45', 360, 100),
]
GRUPOS_SULFURO = [
    (1, 7, '% Extracción Parcelas 1-7: Lado Este', 'A3', 400, 100),
    (8, 14, '% Extracción Parcelas 8-14: Lado Este', 'M3', 400, 100),
    (15, 21, '% Extracción Parcelas 15-21: Lado Oeste', 'A47', 390, 100),
    (22, 28, '% Extracción Parcelas 22-28: Lado Oeste', 'M47', 390, 100),
]
GRUPOS = {'OXIDOS': GRUPOS_OXIDO, 'SULFUROS': GRUPOS_SULFURO}
TAMANO = {'OXIDOS': (25.5, 18.0), 'SULFUROS': (24.5, 18.5)}
ANCLA_VIRTUAL = {'OXIDOS': 'B87', 'SULFUROS': 'A91'}

# Titulos de los graficos "Recuperacion vs RL" (el oficial rotula distinto los
# ultimos; aqui cada grupo lleva su rango real).
TITULOS_RL = {
    'OXIDOS': ['Recuperación vs RL (P1-8 Oxidos)', 'Recuperación vs RL (P9-16 Oxidos)',
               'Recuperación vs RL (P17-24 Oxidos)', 'Recuperación vs RL (P25-32 Oxidos)'],
    'SULFUROS': ['Recuperación vs RL (P1-7 Sulfuros)', 'Recuperación vs RL (P8-14 Sulfuros)',
                 'Recuperación vs RL (P15-21 Sulfuros)', 'Recuperación vs RL (P22-28 Sulfuros)'],
}
Y_MAX_RL = {'OXIDOS': [80, 90, 80, 90], 'SULFUROS': [80, 80, 80, 80]}
TAMANO_RL = (13.0, 8.5)

_ACENTOS = ['accent1', 'accent2', 'accent3', 'accent4', 'accent5', 'accent6']


def _color(idx):
    """Acentos del tema; a partir del septimo, los mismos oscurecidos."""
    scheme = SchemeColor(val=_ACENTOS[idx % 6])
    if idx >= 6:
        scheme.lumMod = 60000
    return ColorChoice(schemeClr=scheme)


def _titulo_con_estilo(chart, titulo):
    chart.title = titulo
    try:
        run = chart.title.tx.rich.p[0].r[0]
        run.rPr = CharacterProperties(sz=1800, b=False, lang='es-CL')
        run.rPr.solidFill = ColorChoice(schemeClr=SchemeColor(val='accent1'))
    except (AttributeError, IndexError):
        pass
    chart.title.overlay = False


def _ceil_to(value, step):
    return int(math.ceil(value / step) * step)


def escala(maximo_datos, maximo_oficial, paso):
    """Maximo del oficial salvo que los datos lo superen (entonces, el siguiente paso)."""
    if maximo_datos is None or not math.isfinite(maximo_datos) or maximo_datos <= maximo_oficial:
        return maximo_oficial
    return _ceil_to(maximo_datos, paso)


def nuevo_grafico(titulo, ancho, alto, eje_x_titulo=None, eje_y_titulo=None,
                  x_max=None, y_max=None, x_min=0, y_min=0, x_unidad=None,
                  y_unidad=None, x_formato='General', leyenda='b', rejilla_x=True):
    """Dispersion suavizada sin marcadores, con el estilo de los graficos oficiales."""
    chart = ScatterChart()
    chart.scatterStyle = 'smoothMarker'
    chart.style = 2
    chart.varyColors = False
    _titulo_con_estilo(chart, titulo)
    chart.width, chart.height = ancho, alto
    chart.x_axis.delete = False
    chart.y_axis.delete = False
    chart.x_axis.majorTickMark = 'none'
    chart.y_axis.majorTickMark = 'none'
    chart.x_axis.number_format = x_formato
    chart.y_axis.number_format = '0'
    if eje_x_titulo:
        chart.x_axis.title = eje_x_titulo
    if eje_y_titulo:
        chart.y_axis.title = eje_y_titulo
    if x_min is not None:
        chart.x_axis.scaling.min = x_min
    if y_min is not None:
        chart.y_axis.scaling.min = y_min
    if x_max is not None:
        chart.x_axis.scaling.max = x_max
    if y_max is not None:
        chart.y_axis.scaling.max = y_max
    if x_unidad:
        chart.x_axis.majorUnit = x_unidad
    if y_unidad:
        chart.y_axis.majorUnit = y_unidad
    if not rejilla_x:
        chart.x_axis.majorGridlines = None
    chart.display_blanks = 'gap'
    if leyenda:
        chart.legend.position = leyenda
    else:
        chart.legend = None
    return chart


def agregar_serie(chart, hoja_x, col_x, hoja_y, col_y, fila_ini, fila_fin,
                  titulo_hoja, titulo_celda, idx):
    """Serie (X = columna col_x, Y = columna col_y) rotulada con una celda."""
    xref = Reference(hoja_x, min_col=col_x, min_row=fila_ini, max_row=fila_fin)
    yref = Reference(hoja_y, min_col=col_y, min_row=fila_ini, max_row=fila_fin)
    serie = Series(yref, xref)
    serie.tx = SeriesLabel(strRef=StrRef(f=titulo_celda))
    serie.marker.symbol = 'none'
    serie.smooth = True
    serie.graphicalProperties = GraphicalProperties()
    serie.graphicalProperties.line = LineProperties(w=19050, cap='rnd', solidFill=_color(idx))
    chart.series.append(serie)
    return serie

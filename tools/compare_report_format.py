# -*- coding: utf-8 -*-
"""Comparador de FORMATO entre un libro generado y el reporte oficial.

Uso::

    python tools/compare_report_format.py generado.xlsx oficial.xlsx
    python tools/compare_report_format.py generado.xlsx --firma test_fixtures/referencias/firma_reporte_oficial.json
    python tools/compare_report_format.py --extraer oficial.xlsx --salida firma.json

Compara, hoja por hoja: nombres, orden y visibilidad; celdas de encabezado
(tipo de contenido y rotulos), formatos numericos, anchos de columna, celdas
combinadas, paneles inmovilizados y graficos (cantidad, tipo, titulo, numero
de series, titulos y escalas de ejes). No compara valores de datos.

La "firma" es un resumen JSON pequeno del libro; el oficial pesa decenas de
MB, asi que se extrae una vez y se versiona la firma. Una firma puede traer,
en cada grafico, un bloque ``esperado`` con el titulo / numero de series que el
generador debe producir a proposito (p.ej. el oficial mezcla series que leen
hojas ocultas o libros externos, que no se replican; ver docs del reporte).

Salida: lista legible de diferencias, cada una ``ERROR`` (rompe el formato
oficial) o ``AVISO`` (estetica / tolerancia). Codigo de salida 0 si no hay
ERROR (con ``--estricto`` tambien fallan los AVISO), 1 si hay diferencias,
2 si no se pudo leer algun libro.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zipfile
from posixpath import join, normpath

from lxml import etree
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter, column_index_from_string

NS = {
    'm': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'xdr': 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing',
    'rel': 'http://schemas.openxmlformats.org/package/2006/relationships',
}

# Hojas visibles del oficial, en orden. Es el contrato del generador.
HOJAS_OFICIALES = [
    'Oxido', 'Sulfuro', 'Dump', 'Rec Ox', 'Rec Ox 2', 'Prod Cu Oxidos',
    '(Cu) dren Ox', 'Flujo Riego Ox', 'RL Oxidos', 'Rec Sulfuro',
    'Rec Sulfuro 2', 'Prod Cu Sulfuros', '(Cu) dren Sulf.',
    'Flujo Riego Sulf', 'RL Sulfuro']

# Filas de encabezado que se leen por hoja (las filas de datos no se comparan).
FILAS_ENCABEZADO = {
    'Oxido': 0, 'Sulfuro': 0, 'Dump': 1, 'Rec Ox': 9, 'Rec Ox 2': 5,
    'Prod Cu Oxidos': 4, '(Cu) dren Ox': 4, 'Flujo Riego Ox': 5,
    'RL Oxidos': 1, 'Rec Sulfuro': 10, 'Rec Sulfuro 2': 4,
    'Prod Cu Sulfuros': 4, '(Cu) dren Sulf.': 4, 'Flujo Riego Sulf': 5,
    'RL Sulfuro': 1}
# Primera fila de datos de cada hoja (para tomar el formato numerico).
FILA_DATOS = {k: v + 1 for k, v in FILAS_ENCABEZADO.items()}
# Columnas leidas en el encabezado: A..F cubre rotulos y las primeras pilas.
COLS_ENCABEZADO = 6
# Funciones de hoja que cuentan como "contenido formula" en el encabezado.
_FUNC = re.compile(r'([A-Z][A-Z0-9.]+)\(')
_EXTERNA = re.compile(r"\[\d+\]")


# ── lectura de paquete ───────────────────────────────────────────────────────

def _xml(zf, name):
    return etree.fromstring(zf.read(name))


def _rels(zf, part):
    """{rId: (tipo, destino absoluto)} de las relaciones de una parte."""
    base, fname = os.path.split(part)
    rel = join(base, '_rels', fname + '.rels')
    if rel not in zf.namelist():
        return {}
    out = {}
    for node in _xml(zf, rel).findall('rel:Relationship', NS):
        target = node.get('Target')
        if node.get('TargetMode') == 'External':
            continue
        path = normpath(join(base, target)) if not target.startswith('/') else target[1:]
        out[node.get('Id')] = (node.get('Type').rsplit('/', 1)[-1], path)
    return out


def _hojas(zf):
    """[(nombre, estado, ruta xml)] en el orden del libro."""
    wb = _xml(zf, 'xl/workbook.xml')
    rels = _rels(zf, 'xl/workbook.xml')
    out = []
    for sheet in wb.find('m:sheets', NS):
        rid = sheet.get('{%s}id' % NS['r'])
        out.append((sheet.get('name'), sheet.get('state') or 'visible', rels[rid][1]))
    return out


def _columnas(root):
    cols = []
    node = root.find('m:cols', NS)
    if node is None:
        return cols
    for col in node.findall('m:col', NS):
        cols.append([int(col.get('min')), int(col.get('max')),
                     round(float(col.get('width') or 0), 2)])
    return cols


def _panel(root):
    pane = root.find('m:sheetViews/m:sheetView/m:pane', NS)
    if pane is None or pane.get('state') not in ('frozen', 'frozenSplit'):
        return None
    x, y = int(float(pane.get('xSplit') or 0)), int(float(pane.get('ySplit') or 0))
    return '%s%d' % (get_column_letter(x + 1), y + 1)


def _color_pestana(root):
    tab = root.find('m:sheetPr/m:tabColor', NS)
    if tab is None:
        return None
    return tab.get('rgb') or ('theme%s' % tab.get('theme'))


def _combinadas(root):
    node = root.find('m:mergeCells', NS)
    if node is None:
        return []
    return sorted(m.get('ref') for m in node.findall('m:mergeCell', NS))


def _texto_rico(node):
    return ''.join(node.xpath('.//a:t/text()', namespaces=NS)).replace('\r', '')


def _norm(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def _eje(ax):
    def val(path):
        got = ax.xpath(path, namespaces=NS)
        return float(got[0]) if got else None
    return dict(
        titulo=_norm(_texto_rico(ax.find('c:title', NS))) if ax.find('c:title', NS) is not None else '',
        min=val('c:scaling/c:min/@val'), max=val('c:scaling/c:max/@val'),
        unidad_mayor=val('c:majorUnit/@val'),
        formato=(ax.xpath('c:numFmt/@formatCode', namespaces=NS) or [None])[0])


def _referencias_serie(ser):
    refs = ser.xpath('c:xVal//c:f/text() | c:yVal//c:f/text() | c:cat//c:f/text() | c:val//c:f/text()',
                     namespaces=NS)
    return [str(r) for r in refs]


def _grafico(zf, part):
    root = _xml(zf, part)
    plot = root.find('c:chart/c:plotArea', NS)
    tipos = [etree.QName(e).localname for e in plot
             if etree.QName(e).localname.endswith('Chart')]
    sers = root.xpath('c:chart/c:plotArea/*/c:ser', namespaces=NS)
    ejes = [_eje(ax) for ax in plot.findall('c:valAx', NS)]
    refs = [_referencias_serie(s) for s in sers]
    externas = sum(1 for r in refs if any(_EXTERNA.search(x) for x in r))
    ocultas = sum(1 for r in refs if any("Budget FY16" in x or '_gr' in x for x in r))
    leyenda = (root.xpath('c:chart/c:legend/c:legendPos/@val', namespaces=NS) or [None])[0]
    return dict(
        tipo=tipos[0] if tipos else None,
        titulo=_norm(_texto_rico(root.find('c:chart/c:title', NS)))
        if root.find('c:chart/c:title', NS) is not None else '',
        series=len(sers), series_externas=externas, series_hojas_ocultas=ocultas,
        ejes=ejes, leyenda=leyenda)


def _graficos_hoja(zf, sheet_part):
    graficos = []
    rels = _rels(zf, sheet_part)
    for rid, (kind, drawing) in rels.items():
        if kind != 'drawing':
            continue
        droot = _xml(zf, drawing)
        drels = _rels(zf, drawing)
        for anchor in droot:
            ids = anchor.xpath('.//c:chart/@r:id', namespaces=NS)
            if not ids:
                continue
            pos = anchor.xpath('xdr:from/xdr:col/text()', namespaces=NS)
            fila = anchor.xpath('xdr:from/xdr:row/text()', namespaces=NS)
            g = _grafico(zf, drels[ids[0]][1])
            g['ancla'] = '%s%d' % (get_column_letter(int(pos[0]) + 1), int(fila[0]) + 1) if pos and fila else None
            graficos.append(g)
    graficos.sort(key=lambda g: (_fila_ancla(g['ancla']), _col_ancla(g['ancla'])))
    return graficos


def _fila_ancla(a):
    m = re.match(r'([A-Z]+)(\d+)', a or '')
    return int(m.group(2)) // 10 if m else 0


def _col_ancla(a):
    m = re.match(r'([A-Z]+)(\d+)', a or '')
    return column_index_from_string(m.group(1)) if m else 0


# ── celdas ───────────────────────────────────────────────────────────────────

def _tipo_celda(value):
    import datetime as _dt
    if value is None:
        return 'vacia', None, None
    if isinstance(value, str):
        if value.startswith('='):
            if _EXTERNA.search(value):
                return 'externa', None, None
            return 'formula', None, sorted(set(_FUNC.findall(value.upper())))
        return 'texto', _norm(value), None
    if isinstance(value, (_dt.datetime, _dt.date)):
        return 'fecha', None, None
    if isinstance(value, bool):
        return 'texto', str(value), None
    return 'numero', None, None


def _celdas_hoja(book, nombre):
    """Encabezado + primera fila de datos de la hoja (nunca recorre todo)."""
    nh = FILAS_ENCABEZADO.get(nombre, 0)
    ndatos = FILA_DATOS.get(nombre, 1)
    if nombre not in book.sheetnames:
        return {}, {}
    ws = book[nombre]
    celdas, formatos = {}, {}
    if nh == 0:
        return celdas, formatos
    for r_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=ndatos,
                                             max_col=COLS_ENCABEZADO), start=1):
        for c_idx, c in enumerate(row, start=1):
            value = getattr(c, 'value', None)
            kind, texto, funcs = _tipo_celda(value)
            if kind == 'vacia':
                continue
            coord = '%s%d' % (get_column_letter(c_idx), r_idx)
            if r_idx <= nh:
                celdas[coord] = dict(
                    tipo=kind, **({'texto': texto} if texto is not None else {}),
                    **({'funciones': funcs} if funcs else {}))
            formatos[coord] = c.number_format
    return celdas, formatos


def extraer_firma(path):
    """Resumen JSON-serializable del formato de un libro."""
    firma = dict(version=1, hojas=[])
    with zipfile.ZipFile(path) as zf:
        hojas = _hojas(zf)
        book = load_workbook(path, read_only=True)
        try:
            for nombre, estado, part in hojas:
                root = _xml(zf, part)
                celdas, formatos = _celdas_hoja(book, nombre)
                firma['hojas'].append(dict(
                    nombre=nombre, estado=estado, panel=_panel(root),
                    color_pestana=_color_pestana(root),
                    columnas=_columnas(root), combinadas=_combinadas(root),
                    encabezado=celdas, formatos=formatos,
                    graficos=_graficos_hoja(zf, part)))
        finally:
            book.close()
    return firma


# ── curacion de la firma ─────────────────────────────────────────────────────
#
# La firma cruda describe el oficial tal cual. Antes de versionarla se "cura"
# con las decisiones de diseno del generador (ver docs del reporte):
#
# * celdas cuyo rotulo es una referencia interna del Excel de origen
#   ("C17 / C18"): se exige un texto, no ese texto;
# * celdas que dependen de otros libros y que el generador no tiene (filas 1, 2
#   y 4 de `Rec Ox 2`, filas 2 y 3 de `Rec Sulfuro 2`): opcionales;
# * graficos: el oficial mezcla series que leen hojas ocultas o libros externos
#   y rotula mal algunos rangos; ``esperado`` fija titulo y numero de series
#   que el generador produce a proposito (una serie por pila del grupo).
TEXTO_LIBRE = {
    'Rec Ox 2': ['B3'], 'Rec Sulfuro 2': ['C1'],
    'Flujo Riego Ox': ['A3'], 'Flujo Riego Sulf': ['A3'],
}
OPCIONALES_FILAS = {
    'Rec Ox 2': [1, 2, 4], 'Rec Sulfuro 2': [2, 3],
}
GRAFICOS_ESPERADOS = {
    'Oxido': [dict(series=8), dict(series=8), dict(series=8), dict(series=8)],
    'Sulfuro': [dict(series=7), dict(series=7), dict(series=7), dict(series=7)],
    'RL Oxidos': [
        dict(series=8, titulo='Recuperación vs RL (P1-8 Oxidos)'),
        dict(series=8, titulo='Recuperación vs RL (P9-16 Oxidos)'),
        dict(series=8, titulo='Recuperación vs RL (P17-24 Oxidos)'),
        dict(series=8, titulo='Recuperación vs RL (P25-32 Oxidos)')],
    'RL Sulfuro': [
        dict(series=7, titulo='Recuperación vs RL (P1-7 Sulfuros)'),
        dict(series=7, titulo='Recuperación vs RL (P8-14 Sulfuros)'),
        dict(series=7, titulo='Recuperación vs RL (P15-21 Sulfuros)'),
        dict(series=7, titulo='Recuperación vs RL (P22-28 Sulfuros)')],
}


def curar_firma(firma):
    """Aplica las decisiones de diseno del generador a una firma cruda."""
    for hoja in firma['hojas']:
        nombre = hoja['nombre']
        for coord in TEXTO_LIBRE.get(nombre, []):
            if coord in hoja['encabezado']:
                hoja['encabezado'][coord]['libre'] = True
        filas = OPCIONALES_FILAS.get(nombre, [])
        for coord, celda in hoja['encabezado'].items():
            if int(re.sub(r'[A-Z]+', '', coord)) in filas:
                celda['opcional'] = True
        for grafico, esperado in zip(hoja['graficos'], GRAFICOS_ESPERADOS.get(nombre, [])):
            grafico['esperado'] = esperado
    firma['curada'] = True
    return firma


# ── comparacion ──────────────────────────────────────────────────────────────

def _compatible(ref, gen):
    """True si el tipo de contenido generado sirve donde el oficial tiene `ref`.

    Una formula del oficial sin funciones (``=+D4+1``) o una referencia a otro
    libro equivalen a un numero escrito; las formulas con funciones (LOOKUP,
    MAX, SUM, COUNTIF) deben seguir siendo formulas.
    """
    if ref['tipo'] == gen['tipo']:
        return True
    numerico = {'numero', 'formula', 'externa'}
    if ref['tipo'] in ('numero', 'externa') and gen['tipo'] in numerico:
        return True
    if ref['tipo'] == 'formula' and not ref.get('funciones') and gen['tipo'] in numerico:
        return True
    return False

def _ancho(columnas, idx):
    for lo, hi, width in columnas:
        if lo <= idx <= hi:
            return width
    return None


def _esperado(grafico, clave, por_defecto):
    return (grafico.get('esperado') or {}).get(clave, por_defecto)


def comparar(gen, ref, tol_ancho=3.0):
    """Lista de (nivel, hoja, mensaje) con las diferencias gen vs ref."""
    dif = []

    def add(nivel, hoja, msg):
        dif.append((nivel, hoja, msg))

    visibles_ref = [h['nombre'] for h in ref['hojas'] if h['estado'] == 'visible']
    visibles_gen = [h['nombre'] for h in gen['hojas'] if h['estado'] == 'visible']
    ocultas_gen = [h['nombre'] for h in gen['hojas'] if h['estado'] != 'visible']
    if visibles_gen != visibles_ref:
        faltan = [n for n in visibles_ref if n not in visibles_gen]
        sobran = [n for n in visibles_gen if n not in visibles_ref]
        if faltan:
            add('ERROR', '*', 'hojas faltantes: %s' % ', '.join(faltan))
        if sobran:
            add('ERROR', '*', 'hojas sobrantes: %s' % ', '.join(sobran))
        comunes_ref = [n for n in visibles_ref if n in visibles_gen]
        comunes_gen = [n for n in visibles_gen if n in visibles_ref]
        if comunes_ref != comunes_gen:
            add('ERROR', '*', 'orden de hojas distinto: %s (generado) vs %s (oficial)'
                % (comunes_gen, comunes_ref))
    if ocultas_gen:
        add('AVISO', '*', 'el generado trae hojas ocultas: %s' % ', '.join(ocultas_gen))

    gen_por = {h['nombre']: h for h in gen['hojas']}
    for rh in ref['hojas']:
        if rh['estado'] != 'visible':
            continue
        nombre = rh['nombre']
        gh = gen_por.get(nombre)
        if gh is None:
            continue
        # encabezado
        for coord, rc in rh['encabezado'].items():
            gc = gh['encabezado'].get(coord)
            if gc is None:
                # un rotulo siempre debe estar; un numero/formula puede faltar
                # si no hay dato de esa pila (columna vacia)
                nivel = 'ERROR' if rc['tipo'] == 'texto' and not rc.get('opcional') else 'AVISO'
                if not rc.get('opcional'):
                    add(nivel, nombre, 'encabezado %s: falta (oficial %s%s)' % (
                        coord, rc['tipo'], ' "%s"' % rc['texto'] if 'texto' in rc else ''))
                continue
            if not _compatible(rc, gc):
                add('ERROR', nombre, 'encabezado %s: tipo %s (generado) vs %s (oficial)'
                    % (coord, gc['tipo'], rc['tipo']))
            elif rc['tipo'] == 'texto' and not rc.get('libre') and gc.get('texto') != rc.get('texto'):
                add('ERROR', nombre, 'encabezado %s: "%s" (generado) vs "%s" (oficial)'
                    % (coord, gc.get('texto'), rc.get('texto')))
            elif rc['tipo'] == 'formula' and rc.get('funciones') and gc.get('funciones') != rc.get('funciones'):
                add('AVISO', nombre, 'encabezado %s: funciones %s vs %s' % (
                    coord, gc.get('funciones'), rc.get('funciones')))
        # formatos numericos
        for coord, fmt in rh['formatos'].items():
            gf = gh['formatos'].get(coord)
            if gf is not None and gf != fmt:
                add('AVISO', nombre, 'formato numerico %s: "%s" vs "%s"' % (coord, gf, fmt))
        # paneles / combinadas / pestana
        if gh['panel'] != rh['panel']:
            add('ERROR', nombre, 'panel inmovilizado %s (generado) vs %s (oficial)'
                % (gh['panel'], rh['panel']))
        if gh['combinadas'] != rh['combinadas']:
            add('ERROR', nombre, 'celdas combinadas %s vs %s' % (gh['combinadas'], rh['combinadas']))
        if gh['color_pestana'] != rh['color_pestana']:
            add('AVISO', nombre, 'color de pestana %s vs %s' % (gh['color_pestana'], rh['color_pestana']))
        # anchos: columnas A..F y primera columna de pilas
        for idx in range(1, COLS_ENCABEZADO + 1):
            rw, gw = _ancho(rh['columnas'], idx), _ancho(gh['columnas'], idx)
            if rw is None or gw is None:
                continue
            if abs(rw - gw) > tol_ancho:
                add('AVISO', nombre, 'ancho columna %s: %.1f vs %.1f (oficial)'
                    % (get_column_letter(idx), gw, rw))
        # graficos
        rg, gg = rh['graficos'], gh['graficos']
        if len(rg) != len(gg):
            add('ERROR', nombre, 'cantidad de graficos %d (generado) vs %d (oficial)' % (len(gg), len(rg)))
        for i, (r, g) in enumerate(zip(rg, gg), start=1):
            tag = 'grafico %d' % i
            if g['tipo'] != r['tipo']:
                add('ERROR', nombre, '%s: tipo %s vs %s' % (tag, g['tipo'], r['tipo']))
            titulo = _esperado(r, 'titulo', r['titulo'])
            if _norm(g['titulo']) != _norm(titulo):
                add('ERROR', nombre, '%s: titulo "%s" vs "%s"' % (tag, g['titulo'], titulo))
            n = _esperado(r, 'series', r['series'])
            if g['series'] != n:
                add('ERROR', nombre, '%s: %d series vs %d esperadas (oficial %d)'
                    % (tag, g['series'], n, r['series']))
            for k, (rax, gax) in enumerate(zip(r['ejes'], g['ejes']), start=1):
                nombre_eje = 'eje %s' % ('X' if k == 1 else 'Y')
                if _norm(gax['titulo']) != _norm(rax['titulo']):
                    add('AVISO', nombre, '%s %s: titulo "%s" vs "%s"' % (
                        tag, nombre_eje, gax['titulo'], rax['titulo']))
                for campo in ('min', 'max'):
                    if rax[campo] is None and campo == 'min':
                        continue                      # escala automatica en el oficial
                    if campo == 'min' and rax[campo] == 0 and gax[campo] is None:
                        continue                      # automatica == 0 con datos >= 0
                    if gax[campo] != rax[campo]:
                        add('AVISO', nombre, '%s %s: %s %s vs %s' % (
                            tag, nombre_eje, campo, gax[campo], rax[campo]))
    return dif


def formatear(dif):
    if not dif:
        return 'Sin diferencias de formato.'
    lineas = []
    por_hoja = {}
    for nivel, hoja, msg in dif:
        por_hoja.setdefault(hoja, []).append((nivel, msg))
    for hoja, items in por_hoja.items():
        lineas.append('[%s]' % hoja)
        for nivel, msg in items:
            lineas.append('  %-6s %s' % (nivel, msg))
    n_err = sum(1 for d in dif if d[0] == 'ERROR')
    lineas.append('')
    lineas.append('%d ERROR, %d AVISO' % (n_err, len(dif) - n_err))
    return '\n'.join(lineas)


def cargar_firma(path):
    with open(path, encoding='utf-8') as fh:
        firma = json.load(fh)
    return firma if firma.get('curada') else curar_firma(firma)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('generado', nargs='?', help='libro generado (.xlsx)')
    ap.add_argument('oficial', nargs='?', help='libro oficial (.xlsx)')
    ap.add_argument('--firma', help='firma JSON del oficial en vez del .xlsx')
    ap.add_argument('--extraer', help='extrae la firma de este libro y termina')
    ap.add_argument('--salida', help='archivo de salida de --extraer')
    ap.add_argument('--estricto', action='store_true',
                    help='los AVISO tambien hacen fallar (codigo 1)')
    args = ap.parse_args(argv)
    try:
        if args.extraer:
            firma = curar_firma(extraer_firma(args.extraer))
            firma = dict(origen='%s (%.1f MB, no versionado). Extraida con '
                         'tools/compare_report_format.py --extraer y curada con curar_firma().'
                         % (os.path.basename(args.extraer),
                            os.path.getsize(args.extraer) / 1e6), **firma)
            texto = json.dumps(firma, ensure_ascii=False, indent=1)
            if args.salida:
                with open(args.salida, 'w', encoding='utf-8') as fh:
                    fh.write(texto)
            else:
                print(texto)
            return 0
        if not args.generado or not (args.oficial or args.firma):
            ap.error('indica generado y oficial (o --firma)')
        ref = cargar_firma(args.firma) if args.firma else curar_firma(extraer_firma(args.oficial))
        gen = extraer_firma(args.generado)
    except (OSError, zipfile.BadZipFile, KeyError, ValueError) as exc:
        print('No se pudo leer un libro: %s' % exc, file=sys.stderr)
        return 2
    dif = comparar(gen, ref)
    print(formatear(dif))
    fallan = [d for d in dif if d[0] == 'ERROR' or args.estricto]
    return 1 if fallan else 0


if __name__ == '__main__':
    sys.exit(main())

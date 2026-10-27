"""Pure helpers for exporting browser-local virtual pile groups."""
from __future__ import annotations

import math

from openpyxl.chart import LineChart, Reference
from openpyxl.chart.axis import DateAxis
from openpyxl.styles import Font


PAD_PREFIX = {'OXIDOS': 'rox', 'SULFUROS': 'rsu'}


class VirtualGroupError(ValueError):
    """A local group is malformed or does not match the active report case."""


def _finite(value):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _pile_id(label, pile):
    prefix = PAD_PREFIX.get(label)
    if not prefix:
        return None
    return f"{prefix}-P{int(pile['num']):02d}"


def build_virtual_groups(doc, groups):
    """Validate every saved local group and aggregate its dated report series.

    Recovery is 100 * sum(member recovered Cu) / sum(member CuTf). Dates with
    an unavailable member stay blank. Group campaigns are deliberately absent.
    """
    if groups is None:
        groups = []
    if not isinstance(groups, list):
        raise VirtualGroupError('El almacenamiento de grupos locales no es una lista válida.')
    all_piles = {}
    for label, pad in (doc.get('pads') or {}).items():
        for pile in (pad or {}).get('pilas', []):
            identifier = _pile_id(label, pile)
            if identifier:
                if identifier in all_piles:
                    raise VirtualGroupError(f'ID de pila duplicado en reporte: {identifier}')
                all_piles[identifier] = pile

    result, seen_ids = [], set()
    for index, group in enumerate(groups or [], start=1):
        if not isinstance(group, dict):
            raise VirtualGroupError(f'Grupo {index}: registro inválido.')
        gid = group.get('id')
        if not isinstance(gid, str) or not gid.strip() or gid in seen_ids:
            raise VirtualGroupError(f'Grupo {index}: ID vacío o duplicado.')
        seen_ids.add(gid)
        name = str(group.get('name') or '').strip()
        members = group.get('members')
        if not name or not isinstance(members, list) or len(members) < 2:
            raise VirtualGroupError(f'Grupo {name or gid}: requiere nombre y al menos dos pilas.')
        if any(not isinstance(member, str) for member in members):
            raise VirtualGroupError(f'Grupo {name}: contiene IDs de pila inválidos.')
        if len(set(members)) != len(members):
            raise VirtualGroupError(f'Grupo {name}: contiene IDs de pila repetidos.')
        unknown = [member for member in members
                   if not isinstance(member, str) or member not in all_piles]
        if unknown:
            raise VirtualGroupError(f'Grupo {name}: pilas no activas en el Caso/reporte: '
                             f'{", ".join(map(str, unknown))}.')
        piles = [all_piles[member] for member in members]
        weights = [_finite(pile.get('apilado')) for pile in piles]
        if any(weight is None or weight <= 0 for weight in weights):
            raise VirtualGroupError(f'Grupo {name}: CuTf no válido en una o más pilas.')
        total_cutf = sum(weights)
        tms_values = [_finite(pile.get('tms')) for pile in piles]
        if any(value is None or value <= 0 for value in tms_values):
            raise VirtualGroupError(f'Grupo {name}: TMS no válidas en una o más pilas.')
        total_tms = sum(tms_values)
        indexed = []
        for member_id, pile in zip(members, piles):
            import pandas as pd
            start = pd.Timestamp(pile['ini']).normalize()
            rec = pile.get('rec') or []
            visible = pile.get('rec_curve')
            if visible is None:
                visible = rec
            rl = pile.get('rl_curve') or []
            daily = {}
            previous = 0.0
            has_previous = True
            for day_index, cumulative in enumerate(rec):
                day = start + pd.Timedelta(days=day_index)
                value = _finite(cumulative)
                shown = _finite(visible[day_index]) if day_index < len(visible) else None
                flow_rl = _finite(rl[day_index]) if day_index < len(rl) else None
                production = value - previous if value is not None and has_previous else None
                if value is not None:
                    previous = value
                    has_previous = True
                else:
                    previous = 0.0
                    has_previous = False
                tms = _finite(pile.get('tms'))
                flow = (flow_rl * tms / 24.0
                        if flow_rl is not None and tms is not None else None)
                daily[day] = (value, shown, production, flow)
            indexed.append((member_id, pile, start, daily))

        dates = sorted(set().union(*(set(series) for _, _, _, series in indexed)))
        rows = []
        for day in dates:
            points = [((0.0, 0.0, 0.0, 0.0) if day < start else series.get(day))
                      for _, _, start, series in indexed]
            complete_rec = all(point is not None and point[0] is not None
                               for point in points)
            complete_visible = all(point is not None and point[1] is not None
                                   for point in points)
            complete_prod = all(point is not None and point[2] is not None
                                for point in points)
            complete_flow = all(point is not None and point[3] is not None
                                for point in points)
            cu_cum = sum(point[0] for point in points) if complete_rec else None
            recovery = (cu_cum / total_cutf * 100.0
                        if complete_rec and complete_visible else None)
            production = sum(point[2] for point in points) if complete_prod else None
            flow = sum(point[3] for point in points) if complete_flow else None
            rate = flow * 24.0 / total_tms if flow is not None and total_tms > 0 else None
            rows.append(dict(date=day, recovery=recovery, cu_cumulative=cu_cum,
                             production=production, flow=flow, rate=rate))
        result.append(dict(id=gid, name=name, members=members[:], piles=piles,
                           total_cutf=total_cutf, total_tms=total_tms,
                           rows=rows, sheet_name=f'Virtual {index:03d}'))
    return result


def write_virtual_sheets(workbook, doc, groups):
    """Write a summary and one data/chart sheet per virtual group."""
    if groups is None or groups == []:
        return 0
    virtual = build_virtual_groups(doc, groups)
    if not virtual:
        return 0
    summary = workbook.create_sheet('Pilas virtuales')
    summary.append(['Pila virtual', 'Miembros (PAD-Pila)', 'CuTf total [t]',
                    'TMS total [t]', 'Cu neto acumulado [t]',
                    'Recuperación [%]', 'Riego acumulado [m3]',
                    'Tasa final [m3/t/día]'])
    for group in virtual:
        members_label = ', '.join(group['members'])
        # Summary uses the actual final date; missing final values remain blank.
        rows = group['rows']
        final_row = rows[-1] if rows else None
        volumes = [_finite(pile.get('vol_riego')) for pile in group['piles']]
        volume = sum(volumes) if all(value is not None for value in volumes) else None
        summary.append([f"[Virtual] {group['name']}", members_label,
                        group['total_cutf'], group['total_tms'],
                        final_row['cu_cumulative'] if final_row else None,
                        final_row['recovery'] if final_row else None, volume,
                        final_row['rate'] if final_row else None])
        ws = workbook.create_sheet(group['sheet_name'][:31])
        ws['A1'] = f"[Virtual] {group['name']}"
        ws['A2'] = f'Miembros: {members_label}'
        ws['A3'] = 'Las columnas no asignan campaña; son sumas de curvas individuales.'
        headers = ['Fecha', 'Recuperación [%]', 'Cu neto acumulado [t]',
                   'Producción neta diaria [t Cu/día]', 'Riego [m3/h]',
                   'Tasa lixiviación [m3/t/día]']
        for col, header in enumerate(headers, start=1):
            ws.cell(row=5, column=col, value=header)
        for row in group['rows']:
            ws.append([row['date'].to_pydatetime(), row['recovery'],
                       row['cu_cumulative'], row['production'], row['flow'], row['rate']])
        for cell in ws[5]:
            cell.font = Font(bold=True)
        for row_index in range(6, 6 + len(group['rows'])):
            ws.cell(row_index, 1).number_format = 'dd-mm-yyyy'
            for col in range(2, 7):
                ws.cell(row_index, col).number_format = '0.000'
        ws.column_dimensions['A'].width = 15
        for col in range(2, 7):
            from openpyxl.utils import get_column_letter
            ws.column_dimensions[get_column_letter(col)].width = 23
        if group['rows']:
            for title, axis, col, anchor in (
                    ('Recuperación virtual', 'Recuperación [%]', 2, 'H1'),
                   ('Producción Cu neto virtual', 'Cu [t/día]', 4, 'H18')):
                chart = LineChart()
                chart.title, chart.y_axis.title = title, axis
                chart.x_axis.title = 'Fecha calendario'
                chart.x_axis = DateAxis(crossAx=100)
                chart.x_axis.title = 'Fecha calendario'
                chart.x_axis.number_format = 'dd-mm-yyyy'
                chart.x_axis.axId = 10
                chart.y_axis.crossAx = 10
                chart.add_data(Reference(ws, min_col=col, min_row=5,
                                         max_row=5 + len(group['rows'])), titles_from_data=True)
                chart.set_categories(Reference(ws, min_col=1, min_row=6,
                                               max_row=5 + len(group['rows'])))
                color = '2A78D6' if col == 2 else 'E86D1F'
                if chart.series:
                    chart.series[0].graphicalProperties.line.solidFill = color
                    chart.series[0].graphicalProperties.line.width = 28575
                ws.add_chart(chart, anchor)
    return len(virtual)


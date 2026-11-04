"""Comparacion de la metodologia de Sulfuros contra el reporte oficial.

Logica pura: no abre conexiones ni escribe en SQL. El CLI
`scripts/comparar_metodo_vs_oficial.py` entrega aqui las filas canonicas
(`sulfide_db_inputs`) y las recuperaciones oficiales leidas del reporte.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path

from .sulfide_method import reconcile_sulfides

SHEET_OFICIAL = 'Oficial_02_12_oct'
YOUNG_MAX_AGE_DAYS = 30


def load_official(xlsx_path=None, history_csv=None, pad='SULFUROS'):
    """{pila: {'YYYY-MM-DD': pct}} desde la hoja oficial del Excel y/o el
    historico oficial validado (CSV). El Excel prevalece en fechas comunes."""
    out = defaultdict(dict)
    if history_csv and Path(history_csv).exists():
        with open(history_csv, encoding='utf-8-sig', newline='') as handle:
            for row in csv.DictReader(handle):
                if row['pad'] == pad:
                    out[row['pile']][row['date']] = float(row['value_pct'])
    if xlsx_path:
        import openpyxl
        book = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
        if SHEET_OFICIAL not in book.sheetnames:
            raise ValueError(f'el Excel no tiene la hoja {SHEET_OFICIAL}')
        for fecha, pad_x, _camp, parcela, value, *_ in book[SHEET_OFICIAL].iter_rows(min_row=2, values_only=True):
            if pad_x == pad and value is not None:
                out[f'P{int(parcela):02d}'][str(fecha)[:10]] = float(value)
    return dict(out)


def compare(rows, target_net_t, window_start, window_end, official, tol_pp=1e-4):
    """Corre la metodologia sobre `rows` y la compara con `official`.

    Devuelve dict con: resumen, filas por pila, filas diarias y verificaciones.
    """
    start, end = str(window_start)[:10], str(window_end)[:10]
    out, audit = reconcile_sulfides(rows, start, end, target_net_t)
    young = {k[1] for k in audit['young']}
    by_pile = defaultdict(dict)
    for source, result in zip(rows, out):
        by_pile[source['pile']][source['date']] = (source, result)
    previous = (date.fromisoformat(start).toordinal() - 1)
    base_day = date.fromordinal(previous).isoformat()

    piles, daily, checks = [], [], []
    held_official = 0.0
    for pile in sorted(by_pile):
        days = by_pile[pile]
        base_row = days[base_day][0]
        end_source, end_result = days[end]
        cu = float(base_row['cu_apilado_t'])
        base = float(base_row['official_pct'])
        measured_end = end_source.get('observed_pct')
        method_end = end_result.get('reconciled_pct')
        off = official.get(pile, {})
        official_end = off.get(end)
        official_base = off.get(base_day)
        net = lambda pct: None if pct is None else cu * (pct - base) / 100
        age = (date.fromisoformat(end) - date.fromisoformat(base_row['first_irrigation'])).days
        record = dict(
            pila=pile, estado='joven' if pile in young else 'madura', edad_dias=age, cu_apilado_t=cu,
            base_pct=base, base_vs_oficial_pp=None if official_base is None else base - official_base,
            medido_fin_pct=measured_end, metodo_fin_pct=method_end, oficial_fin_pct=official_end,
            metodo_menos_oficial_pp=None if official_end is None or method_end is None else method_end - official_end,
            medido_menos_oficial_pp=None if official_end is None or measured_end is None else measured_end - official_end,
            cu_neto_metodo_t=net(method_end),
            cu_neto_oficial_t=None if official_end is None else cu * (official_end - base) / 100,
        )
        piles.append(record)
        if pile not in young and record['cu_neto_oficial_t'] is not None:
            held_official += record['cu_neto_oficial_t']
        for day in sorted(days):
            if day < start:
                continue
            source, result = days[day]
            method = result.get('reconciled_pct')
            reference = off.get(day)
            daily.append(dict(pila=pile, fecha=day, estado=record['estado'],
                              medido_pct=source.get('observed_pct'), metodo_pct=method, oficial_pct=reference,
                              metodo_menos_oficial_pp=None if reference is None or method is None else method - reference))
            if pile not in young and method is not None and source.get('observed_pct') is not None \
                    and abs(method - source['observed_pct']) > 1e-12:
                checks.append(('madura_conserva_medido_exacto', False, f'{pile} {day}'))
    checks.append(('madura_conserva_medido_exacto', not any(c[1] is False for c in checks), 'todas las maduras'))
    checks.insert(0, ('cierre_neto_F29', abs(audit['net_residual_t']) < 1e-6,
                      f"residuo {audit['net_residual_t']:.3e} t"))

    official_net = sum(r['cu_neto_oficial_t'] for r in piles if r['cu_neto_oficial_t'] is not None)
    official_young = sum(r['cu_neto_oficial_t'] for r in piles if r['estado'] == 'joven' and r['cu_neto_oficial_t'] is not None)
    delivered_young = sum(r['cu_neto_metodo_t'] for r in piles if r['estado'] == 'joven' and r['cu_neto_metodo_t'] is not None)
    missing = [r['pila'] for r in piles if r['oficial_fin_pct'] is None]
    summary = dict(
        ventana=f'{start}..{end}', objetivo_F29_t=float(target_net_t), lambda_=audit['lambda'],
        residuo_cierre_t=audit['net_residual_t'], jovenes=sorted(young), maduras=sorted(by_pile.keys() - young),
        cu_neto_maduras_oficial_t=held_official,
        cu_neto_jovenes_metodo_t=delivered_young, cu_neto_jovenes_oficial_t=official_young,
        cu_neto_total_oficial_t=official_net, brecha_oficial_vs_F29_t=float(target_net_t) - official_net,
        pilas_sin_dato_oficial=missing,
        max_abs_medido_vs_oficial_maduras_pp=max(
            (abs(r['medido_menos_oficial_pp']) for r in piles if r['estado'] == 'madura' and r['medido_menos_oficial_pp'] is not None),
            default=None),
        max_abs_metodo_vs_oficial_jovenes_pp=max(
            (abs(r['metodo_menos_oficial_pp']) for r in piles if r['estado'] == 'joven' and r['metodo_menos_oficial_pp'] is not None),
            default=None),
    )
    if summary['max_abs_medido_vs_oficial_maduras_pp'] is not None:
        checks.append(('maduras_medido_igual_oficial', summary['max_abs_medido_vs_oficial_maduras_pp'] <= tol_pp,
                       f"max {summary['max_abs_medido_vs_oficial_maduras_pp']:.4f} pp (tol {tol_pp})"))
    checks.append(('oficial_disponible_en_todas_las_pilas', not missing, ', '.join(missing) or 'ok'))
    return dict(summary=summary, piles=piles, daily=daily, checks=checks)


def render_markdown(result, caso=None):
    s = result['summary']
    f = lambda v, n=3: '—' if v is None else f'{v:.{n}f}'
    lines = [f"# Metodología de Sulfuros vs reporte oficial — {caso or ''}".rstrip(),
             '', f"Ventana {s['ventana']} · objetivo F29 {s['objetivo_F29_t']:.3f} t Cu · λ={f(s['lambda_'], 6)} · "
                 f"residuo de cierre {s['residuo_cierre_t']:.2e} t", '',
             f"- Jóvenes (≤{YOUNG_MAX_AGE_DAYS} d, ajustadas): {', '.join(s['jovenes']) or 'ninguna'}",
             f"- Cu neto oficial de las maduras: {f(s['cu_neto_maduras_oficial_t'], 2)} t",
             f"- Cu neto de las jóvenes: método {f(s['cu_neto_jovenes_metodo_t'], 2)} t · oficial {f(s['cu_neto_jovenes_oficial_t'], 2)} t",
             f"- Total oficial {f(s['cu_neto_total_oficial_t'], 2)} t → brecha contra F29 {f(s['brecha_oficial_vs_F29_t'], 2)} t", '',
             '| Pila | Estado | Edad | Cu apilado t | Base % | Medido fin % | Método fin % | Oficial fin % | Método−Oficial pp | Medido−Oficial pp | Cu neto método t | Cu neto oficial t |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in result['piles']:
        lines.append(f"| {r['pila']} | {r['estado']} | {r['edad_dias']} | {r['cu_apilado_t']:.1f} | {f(r['base_pct'])} | "
                     f"{f(r['medido_fin_pct'])} | {f(r['metodo_fin_pct'])} | {f(r['oficial_fin_pct'])} | "
                     f"{f(r['metodo_menos_oficial_pp'])} | {f(r['medido_menos_oficial_pp'])} | "
                     f"{f(r['cu_neto_metodo_t'], 2)} | {f(r['cu_neto_oficial_t'], 2)} |")
    lines += ['', '## Verificaciones', '']
    lines += [f"- {'OK ' if ok else 'FALLA'} `{name}` — {detail}" for name, ok, detail in result['checks']]
    return '\n'.join(lines) + '\n'


def write_outputs(result, folder, caso=None):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for name, key in (('resumen_por_pila.csv', 'piles'), ('detalle_diario.csv', 'daily')):
        with open(folder / name, 'w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(result[key][0]))
            writer.writeheader()
            writer.writerows(result[key])
    (folder / 'RESULTADO.md').write_text(render_markdown(result, caso), encoding='utf-8')
    return folder

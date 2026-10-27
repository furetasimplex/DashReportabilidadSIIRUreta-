"""Complete physical columns and weighted group overlays for Excel reports."""
from copy import deepcopy

from .virtual_pile_report import build_virtual_groups
from .rl_series import cumulative_campaign_rl
import pandas as pd


def physical_columns(doc, label, order):
    piles = {int(q['num']): q for q in doc.get('pads', {}).get(label, {}).get('pilas', [])}
    numbers = list(order) + sorted(set(piles) - set(order))
    result = []
    for num in numbers:
        if num in piles:
            result.append(piles[num])
        else:
            result.append(dict(num=num, p=f'P{num:02d}', campana=None, n=0,
                apilado=None, planta_rec_termino=None, t_rec=None, t_med=None,
                rec=[], rec_curve=[], rl_curve=[], tms=None,
                ini=doc.get('pads', {}).get(label, {}).get('desde') or doc['end']))
    return result


def recovery_columns(doc, label, order):
    return physical_columns(doc, label, order) + doc.get('group_columns', {}).get(label, [])


def with_group_columns(doc, groups):
    """Create a presentation copy; group overlays never enter physical totals."""
    if not groups:
        return doc
    result = deepcopy(doc)
    result['group_columns'] = {'OXIDOS': [], 'SULFUROS': []}
    for group in build_virtual_groups(doc, groups):
        pads = {m.split('-P')[0] for m in group['members']}
        name = f"Σ {group['name']}" + (' [OX+SU]' if len(pads) > 1 else '')
        rows = group['rows']
        pile = dict(p=name, num=name, virtual=True, members=group['members'],
            campana=None, n=len(rows), apilado=group['total_cutf'],
            planta_rec_termino=None,
            t_rec=rows[-1]['cu_cumulative'] if rows else None,
            rec=[r['cu_cumulative'] for r in rows],
            rec_curve=[r['cu_cumulative'] if r['recovery'] is not None else None for r in rows])
        pile['ini'] = str(pd.Timestamp(rows[0]['date']).date()) if rows else doc['end']
        pile['rl_curve'] = [r['rate'] for r in rows]
        flows, masses, starts = {}, {}, {}
        for i, member in enumerate(group['piles']):
            key = str(i)
            masses[key] = member['tms']
            starts[key] = member['ini']
            flows[key] = {pd.Timestamp(member['ini']) + pd.Timedelta(days=j):
                          (value * member['tms'] / 24 if value is not None else None)
                          for j, value in enumerate(member.get('rl_curve') or [])}
        cumulative = cumulative_campaign_rl(flows, masses, starts)
        pile['rl_accum_curve'] = [cumulative.get(pd.Timestamp(r['date']).normalize()) for r in rows]
        # A mixed overlay is explicitly labelled in both views, never pad totals.
        for prefix, label in [('rox', 'OXIDOS'), ('rsu', 'SULFUROS')]:
            if prefix in pads:
                result['group_columns'][label].append(pile)
    return result
